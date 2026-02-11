import asyncio
import json
import logging
import os
from pathlib import Path
from typing import AsyncGenerator, Dict, List
from uuid import uuid4

from browser_use import Agent, Browser, ChatOpenAI, Tools, BrowserProfile, ActionResult
from pydantic import BaseModel

from prompts import get_prompt
from schemas import AgentRequest, BatchOrderRequest, BatchItemResult

logger = logging.getLogger(__name__)

# --- Global State for HITL ---
# Maps session_id -> asyncio.Future
# When the agent needs input, it creates a future and awaits it.
# The API /agent/input resolves this future.
_pending_inputs: Dict[str, asyncio.Future] = {}

# Reusable browser instance
_browser = None

MAX_STEPS = 25   # Hard limit for agent steps

# Persistent browser profile directory - stores cookies, login sessions, etc.
BROWSER_PROFILE_DIR = Path(__file__).parent / "browser_profile"
BROWSER_PROFILE_DIR.mkdir(exist_ok=True)

async def get_browser():
    global _browser
    # Always create a fresh browser instance for each session
    # to avoid CDP connection issues
    _browser = Browser(
        browser_profile=BrowserProfile(
            headless=os.getenv("HEADLESS", "false").lower() == "true",
            user_data_dir=str(BROWSER_PROFILE_DIR),  # Persist cookies, login sessions
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ]
        )
    )
    return _browser

# --- Pydantic Models for HITL Tools ---

class AskUserArgs(BaseModel):
    question: str

class ProductOption(BaseModel):
    product_name: str
    price: str
    rating: str
    product_url: str

class ShowProductChoicesArgs(BaseModel):
    products: List[ProductOption]
    message: str = "Please select a product:"

class AddressOption(BaseModel):
    name: str
    phone: str = ""
    address: str
    address_type: str = ""  # HOME, WORK, etc.

class ShowAddressChoicesArgs(BaseModel):
    addresses: List[AddressOption]
    message: str = "Please select a delivery address:"

class PaymentOption(BaseModel):
    method: str  # COD, UPI, Card, etc.
    description: str = ""

class ShowPaymentChoicesArgs(BaseModel):
    payments: List[PaymentOption]
    message: str = "Please select a payment method:"

class OptionItem(BaseModel):
    label: str
    description: str = ""
    value: str = ""

class ShowOptionsArgs(BaseModel):
    options: List[OptionItem]
    message: str
    option_type: str = "general"  # "general", "warning", "info", "action"

# --- Streaming Generator ---

async def stream_agent_events(request: AgentRequest) -> AsyncGenerator[str, None]:
    session_id = request.session_id or str(uuid4())
    browser = await get_browser()

    # Determine temperature based on action type
    # - Order actions: 0.0 for fully deterministic behavior (MUST follow prompts exactly)
    # - Search actions: slightly higher (0.2) for better product matching
    # - User can override with custom temperature
    if request.temperature is not None:
        temperature = max(0.0, min(1.0, request.temperature))  # Clamp between 0 and 1
    elif request.action == "order":
        temperature = 0.0  # Fully deterministic - MUST follow prompts exactly
    else:
        temperature = 0.2  # Slightly more flexible for search

    # Initialize LLM with temperature
    llm = ChatOpenAI(model="gpt-4o", temperature=temperature)

    logger.info(f"Starting agent with temperature={temperature} for action={request.action}")

    # Validate order action has product_url
    if request.action == "order" and not request.product_url:
        yield f"data: {json.dumps({'type': 'error', 'content': 'Product URL required for order action'})}\n\n"
        return

    # Get the appropriate task and extend_system_message
    try:
        prompt_config = get_prompt(
            platform=request.platform,
            action=request.action,
            product_url=request.product_url,
            query=request.user_message if request.action == "search" else None,
            additional_instructions=request.user_message if request.action == "order" else None,
            quantity=request.quantity if request.action == "order" else 1,
            color=request.color if request.action == "order" else None
        )
        task = prompt_config["task"]
        extend_system_message = prompt_config["extend_system_message"]
    except ValueError as e:
        yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
        return

    # Send initial config info to frontend
    yield f"data: {json.dumps({'type': 'config', 'content': {'temperature': temperature, 'action': request.action, 'platform': request.platform}})}\n\n"

    # --- Dynamic Tools with Closure for Session ID ---
    # Create Tools instance for this session to capture session_id in closures
    local_tools = Tools()

    @local_tools.action(
        "Ask the user for information or confirmation. Use this for OTP, Login credentials, cart confirmation, or any human input.",
        param_model=AskUserArgs
    )
    async def ask_user_tool(params: AskUserArgs) -> ActionResult:
        question = params.question
        logger.info(f"Asking user: {question}")

        loop = asyncio.get_running_loop()
        future = loop.create_future()
        _pending_inputs[session_id] = future

        event_queue.put_nowait({
            "type": "request_input",
            "content": question,
            "session_id": session_id
        })

        result = await future
        user_response = result.strip().lower()

        # Check for affirmative responses
        if user_response in ['yes', 'y', 'ok', 'okay', 'sure', 'proceed', 'go ahead', 'add', 'add to cart', 'confirm']:
            return ActionResult(
                extracted_content=f"USER CONFIRMED: '{result}'. Proceed with the action. Do NOT ask again."
            )
        # Check for negative responses
        elif user_response in ['no', 'n', 'cancel', 'stop', 'dont', "don't", 'never mind']:
            return ActionResult(
                extracted_content=f"USER DECLINED: '{result}'. Do NOT proceed. Inform user you cancelled."
            )
        else:
            # For other inputs (OTP, phone number, password)
            return ActionResult(
                extracted_content=f"USER PROVIDED: '{result}'. Use this value. Do NOT ask again."
            )

    @local_tools.action(
        "Show product options to user and get their choice. Terminates the task with selected product.",
        param_model=ShowProductChoicesArgs
    )
    async def show_product_choices(params: ShowProductChoicesArgs) -> ActionResult:
        logger.info(f"Showing {len(params.products)} product choices to user")

        loop = asyncio.get_running_loop()
        future = loop.create_future()
        _pending_inputs[session_id] = future

        event_queue.put_nowait({
            "type": "product_choices",
            "content": {
                "message": params.message,
                "products": [p.model_dump() for p in params.products]
            },
            "session_id": session_id
        })

        result = await future

        try:
            selected_idx = int(result)
            if 0 <= selected_idx < len(params.products):
                selected = params.products[selected_idx]
                product_json = json.dumps({
                    "product_name": selected.product_name,
                    "price": selected.price,
                    "rating": selected.rating,
                    "product_url": selected.product_url
                })
                # is_done=True terminates the agent with this result
                return ActionResult(
                    extracted_content=product_json,
                    is_done=True,
                    success=True
                )
        except (ValueError, IndexError):
            pass

        return ActionResult(extracted_content=f"User response: {result}")

    @local_tools.action(
        "MANDATORY: Show delivery address options to user. You MUST call this when you see address/delivery page. NEVER click 'Deliver Here' without calling this first.",
        param_model=ShowAddressChoicesArgs
    )
    async def show_address_choices(params: ShowAddressChoicesArgs) -> ActionResult:
        logger.info(f"Showing {len(params.addresses)} address choices to user")

        loop = asyncio.get_running_loop()
        future = loop.create_future()
        _pending_inputs[session_id] = future

        event_queue.put_nowait({
            "type": "address_choices",
            "content": {
                "message": params.message,
                "addresses": [a.model_dump() for a in params.addresses]
            },
            "session_id": session_id
        })

        result = await future

        try:
            selected_idx = int(result)
            if 0 <= selected_idx < len(params.addresses):
                selected = params.addresses[selected_idx]

                if selected.address_type == "NEW" or "Add New Address" in selected.name:
                    return ActionResult(
                        extracted_content="USER WANTS NEW ADDRESS. Click '+ Add a new address', then ask for: Full Name, Phone, Pincode, Address, City, State."
                    )

                return ActionResult(
                    extracted_content=f"USER SELECTED ADDRESS #{selected_idx + 1}: {selected.name}, {selected.address}. ACTION REQUIRED: Check if this address already has 'Deliver Here' button visible. If YES → click 'Deliver Here' directly. If NO → first click the RADIO BUTTON next to this address, wait 2 seconds for 'Deliver Here' to appear, then click it."
                )
        except (ValueError, IndexError):
            pass

        return ActionResult(extracted_content=f"User response: {result}")

    @local_tools.action(
        "MANDATORY: Show payment method options to user. You MUST call this when you see payment page. NEVER select a payment method without calling this first.",
        param_model=ShowPaymentChoicesArgs
    )
    async def show_payment_choices(params: ShowPaymentChoicesArgs) -> ActionResult:
        logger.info(f"Showing {len(params.payments)} payment choices to user")

        loop = asyncio.get_running_loop()
        future = loop.create_future()
        _pending_inputs[session_id] = future

        event_queue.put_nowait({
            "type": "payment_choices",
            "content": {
                "message": params.message,
                "payments": [p.model_dump() for p in params.payments]
            },
            "session_id": session_id
        })

        result = await future

        try:
            selected_idx = int(result)
            if 0 <= selected_idx < len(params.payments):
                selected = params.payments[selected_idx]
                return ActionResult(
                    extracted_content=f"USER SELECTED PAYMENT: {selected.method}. Click this payment option on the page."
                )
        except (ValueError, IndexError):
            pass

        return ActionResult(extracted_content=f"User response: {result}")

    @local_tools.action(
        "MANDATORY: Show quantity/variant options to user. You MUST call this when you see quantity selector or product variants. NEVER select quantity without calling this first.",
        param_model=ShowOptionsArgs
    )
    async def show_options(params: ShowOptionsArgs) -> ActionResult:
        logger.info(f"Showing {len(params.options)} options to user: {params.message}")

        loop = asyncio.get_running_loop()
        future = loop.create_future()
        _pending_inputs[session_id] = future

        event_queue.put_nowait({
            "type": "options",
            "content": {
                "message": params.message,
                "options": [o.model_dump() for o in params.options],
                "option_type": params.option_type
            },
            "session_id": session_id
        })

        result = await future

        try:
            selected_idx = int(result)
            if 0 <= selected_idx < len(params.options):
                selected = params.options[selected_idx]
                value = selected.value if selected.value else selected.label
                return ActionResult(
                    extracted_content=f"USER SELECTED: {selected.label} (value: {value}). Proceed with this selection."
                )
        except (ValueError, IndexError):
            pass

        return ActionResult(extracted_content=f"User response: {result}")

    # Event Queue for streaming
    event_queue = asyncio.Queue()

    # Step counter for limit enforcement
    step_counter = 0

    # Step Callback with step limit logic
    async def step_callback(state, output, step_idx):
        nonlocal step_counter
        step_counter += 1

        # Check if max steps reached and force stop
        if step_counter >= MAX_STEPS:
            logger.warning(f"Max steps ({MAX_STEPS}) reached. Forcing stop.")
            await agent.stop(
                f"STOPPED: Maximum step limit ({MAX_STEPS}) reached. Task terminated."
            )
            return

        # This runs every step
        # expected_output is AgentOutput, looking into it for thoughts/logs.
        try:
            thought = output.current_state.thinking if output and output.current_state else "Processing..."
            event_queue.put_nowait({
                "type": "log",
                "content": f"Step {step_counter}/{MAX_STEPS}: {thought}"
            })
        except Exception as e:
            logger.warning(f"Error in step_callback: {e}")
            event_queue.put_nowait({
                "type": "log",
                "content": f"Step {step_counter}/{MAX_STEPS}: Processing..."
            })

    agent = Agent(
        task=task,
        llm=llm,
        browser=browser,
        tools=local_tools,
        extend_system_message=extend_system_message,
        register_new_step_callback=step_callback,
        max_steps=MAX_STEPS,
        max_failures=3,
        max_actions_per_step=4,
        calculate_cost=True,  # Enable token/cost tracking
    )

    # Run agent in background task so we can consume the queue
    async def run_agent_task():
        try:
            history = await agent.run()
            result = history.final_result()

            # Send result
            event_queue.put_nowait({
                "type": "result",
                "content": str(result)
            })

            # Send token usage stats
            try:
                usage = history.usage
                if usage:
                    event_queue.put_nowait({
                        "type": "usage",
                        "content": {
                            "input_tokens": usage.total_prompt_tokens,
                            "output_tokens": usage.total_completion_tokens,
                            "total_tokens": usage.total_tokens,
                            "total_cost": usage.total_cost,
                            "steps": step_counter
                        }
                    })
                    logger.info(f"Token usage - Input: {usage.total_prompt_tokens}, Output: {usage.total_completion_tokens}, Total: {usage.total_tokens}, Cost: ${usage.total_cost:.4f}")
                else:
                    logger.warning("No usage data available from agent history")
                    event_queue.put_nowait({
                        "type": "usage",
                        "content": {
                            "steps": step_counter
                        }
                    })
            except Exception as usage_err:
                logger.warning(f"Could not get usage stats: {usage_err}")
                # Send basic step count even if usage fails
                event_queue.put_nowait({
                    "type": "usage",
                    "content": {
                        "steps": step_counter
                    }
                })
        except Exception as e:
            event_queue.put_nowait({
                "type": "error",
                "content": str(e)
            })
        finally:
            # Clean up any pending input futures for this session
            if session_id in _pending_inputs:
                future = _pending_inputs.pop(session_id)
                if not future.done():
                    future.cancel()
            event_queue.put_nowait(None) # Sentinel

    # Start the agent
    asyncio.create_task(run_agent_task())

    # Yield from queue
    while True:
        event = await event_queue.get()
        if event is None:
            break
        yield f"data: {json.dumps(event)}\n\n"

async def provide_input(session_id: str, input_data: str):
    if session_id in _pending_inputs:
        future = _pending_inputs[session_id]
        if not future.done():
            future.set_result(input_data)
        del _pending_inputs[session_id]
        return {"status": "success"}
    return {"status": "error", "message": "No pending input for this session"}


# --- Batch Order Processing ---

async def stream_batch_order_events(request: BatchOrderRequest) -> AsyncGenerator[str, None]:
    """
    Process multiple orders in sequence.
    Uses a SINGLE browser instance for all items (more efficient).
    Browser stays open until ALL items are processed.
    """
    batch_session_id = request.session_id or str(uuid4())

    # Results tracking
    results: List[BatchItemResult] = []
    for idx, item in enumerate(request.items):
        results.append(BatchItemResult(
            index=idx,
            product_url=item.product_url,
            quantity=item.quantity,
            color=item.color,
            status="pending"
        ))

    # Initialize batch config
    temperature = request.temperature if request.temperature is not None else 0.0
    llm = ChatOpenAI(model="gpt-4o", temperature=temperature)

    # Send initial batch config
    yield f"data: {json.dumps({'type': 'batch_start', 'content': {'total_items': len(request.items), 'platform': request.platform, 'session_id': batch_session_id}})}\n\n"

    # Send initial results state
    yield f"data: {json.dumps({'type': 'batch_status', 'content': [r.model_dump() for r in results]})}\n\n"

    yield f"data: {json.dumps({'type': 'log', 'content': f'Starting batch processing of {len(request.items)} items'})}\n\n"

    # Create a SINGLE browser instance for ALL items
    # keep_alive=True prevents browser reset between agent runs
    # user_data_dir persists cookies and login sessions
    browser = Browser(
        browser_profile=BrowserProfile(
            headless=os.getenv("HEADLESS", "false").lower() == "true",
            keep_alive=True,  # Prevents browser from being reset after each agent completes
            user_data_dir=str(BROWSER_PROFILE_DIR),  # Persist cookies, login sessions
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ]
        )
    )

    yield f"data: {json.dumps({'type': 'log', 'content': 'Browser opened - will remain open for all items'})}\n\n"

    # Track total usage across all batch items
    total_batch_usage = {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "total_cost": 0,
        "total_steps": 0
    }

    try:
        # Process each item sequentially using the SAME browser
        for idx, item in enumerate(request.items):
            item_session_id = f"{batch_session_id}_item_{idx}"

            # Update status to in_progress
            results[idx].status = "in_progress"
            yield f"data: {json.dumps({'type': 'batch_status', 'content': [r.model_dump() for r in results]})}\n\n"
            yield f"data: {json.dumps({'type': 'log', 'content': f'Starting item {idx + 1}/{len(request.items)}: {item.product_url}'})}\n\n"

            try:
                # Get prompt for this item
                prompt_config = get_prompt(
                    platform=request.platform,
                    action="order",
                    product_url=item.product_url,
                    additional_instructions=request.additional_instructions,
                    quantity=item.quantity,
                    color=item.color
                )
                task = prompt_config["task"]
                extend_system_message = prompt_config["extend_system_message"]

                # Create tools for this item's session
                local_tools = Tools()
                event_queue = asyncio.Queue()

                # Capture idx and item_session_id in closures
                current_idx = idx
                current_session_id = item_session_id

                @local_tools.action(
                    "Ask the user for information or confirmation. Use this for OTP, Login credentials, cart confirmation, or any human input.",
                    param_model=AskUserArgs
                )
                async def ask_user_tool(params: AskUserArgs, _idx=current_idx, _sid=current_session_id) -> ActionResult:
                    question = params.question
                    logger.info(f"[Batch Item {_idx}] Asking user: {question}")

                    loop = asyncio.get_running_loop()
                    future = loop.create_future()
                    _pending_inputs[_sid] = future

                    event_queue.put_nowait({
                        "type": "request_input",
                        "content": question,
                        "session_id": _sid,
                        "batch_item_index": _idx
                    })

                    result = await future
                    user_response = result.strip().lower()

                    if user_response in ['yes', 'y', 'ok', 'okay', 'sure', 'proceed', 'go ahead', 'add', 'add to cart', 'confirm']:
                        return ActionResult(extracted_content=f"USER CONFIRMED: '{result}'. Proceed with the action. Do NOT ask again.")
                    elif user_response in ['no', 'n', 'cancel', 'stop', 'dont', "don't", 'never mind']:
                        return ActionResult(extracted_content=f"USER DECLINED: '{result}'. Do NOT proceed. Inform user you cancelled.")
                    else:
                        return ActionResult(extracted_content=f"USER PROVIDED: '{result}'. Use this value. Do NOT ask again.")

                @local_tools.action(
                    "MANDATORY: Show delivery address options to user.",
                    param_model=ShowAddressChoicesArgs
                )
                async def show_address_choices(params: ShowAddressChoicesArgs, _idx=current_idx, _sid=current_session_id) -> ActionResult:
                    logger.info(f"[Batch Item {_idx}] Showing {len(params.addresses)} address choices")

                    loop = asyncio.get_running_loop()
                    future = loop.create_future()
                    _pending_inputs[_sid] = future

                    event_queue.put_nowait({
                        "type": "address_choices",
                        "content": {"message": params.message, "addresses": [a.model_dump() for a in params.addresses]},
                        "session_id": _sid,
                        "batch_item_index": _idx
                    })

                    result = await future
                    try:
                        selected_idx = int(result)
                        if 0 <= selected_idx < len(params.addresses):
                            selected = params.addresses[selected_idx]
                            if selected.address_type == "NEW" or "Add New Address" in selected.name:
                                return ActionResult(extracted_content="USER WANTS NEW ADDRESS. Click '+ Add a new address', then ask for: Full Name, Phone, Pincode, Address, City, State.")
                            return ActionResult(extracted_content=f"USER SELECTED ADDRESS #{selected_idx + 1}: {selected.name}, {selected.address}. Click 'DELIVER HERE' for this address.")
                    except (ValueError, IndexError):
                        pass
                    return ActionResult(extracted_content=f"User response: {result}")

                @local_tools.action(
                    "MANDATORY: Show payment method options to user.",
                    param_model=ShowPaymentChoicesArgs
                )
                async def show_payment_choices(params: ShowPaymentChoicesArgs, _idx=current_idx, _sid=current_session_id) -> ActionResult:
                    logger.info(f"[Batch Item {_idx}] Showing {len(params.payments)} payment choices")

                    loop = asyncio.get_running_loop()
                    future = loop.create_future()
                    _pending_inputs[_sid] = future

                    event_queue.put_nowait({
                        "type": "payment_choices",
                        "content": {"message": params.message, "payments": [p.model_dump() for p in params.payments]},
                        "session_id": _sid,
                        "batch_item_index": _idx
                    })

                    result = await future
                    try:
                        selected_idx = int(result)
                        if 0 <= selected_idx < len(params.payments):
                            selected = params.payments[selected_idx]
                            return ActionResult(extracted_content=f"USER SELECTED PAYMENT: {selected.method}. Click this payment option on the page.")
                    except (ValueError, IndexError):
                        pass
                    return ActionResult(extracted_content=f"User response: {result}")

                @local_tools.action(
                    "MANDATORY: Show options to user.",
                    param_model=ShowOptionsArgs
                )
                async def show_options(params: ShowOptionsArgs, _idx=current_idx, _sid=current_session_id) -> ActionResult:
                    logger.info(f"[Batch Item {_idx}] Showing {len(params.options)} options: {params.message}")

                    loop = asyncio.get_running_loop()
                    future = loop.create_future()
                    _pending_inputs[_sid] = future

                    event_queue.put_nowait({
                        "type": "options",
                        "content": {"message": params.message, "options": [o.model_dump() for o in params.options], "option_type": params.option_type},
                        "session_id": _sid,
                        "batch_item_index": _idx
                    })

                    result = await future
                    try:
                        selected_idx = int(result)
                        if 0 <= selected_idx < len(params.options):
                            selected = params.options[selected_idx]
                            value = selected.value if selected.value else selected.label
                            return ActionResult(extracted_content=f"USER SELECTED: {selected.label} (value: {value}). Proceed with this selection.")
                    except (ValueError, IndexError):
                        pass
                    return ActionResult(extracted_content=f"User response: {result}")

                # Step counter and callback
                step_counter = 0

                async def step_callback(state, output, step_idx, _idx=current_idx):
                    nonlocal step_counter
                    step_counter += 1

                    if step_counter >= MAX_STEPS:
                        logger.warning(f"[Batch Item {_idx}] Max steps ({MAX_STEPS}) reached.")
                        await agent.stop(f"STOPPED: Maximum step limit ({MAX_STEPS}) reached.")
                        return

                    try:
                        thought = output.current_state.thinking if output and output.current_state else "Processing..."
                        event_queue.put_nowait({
                            "type": "log",
                            "content": f"[Item {_idx + 1}] Step {step_counter}/{MAX_STEPS}: {thought}"
                        })
                    except Exception as e:
                        logger.warning(f"Error in step_callback: {e}")
                        event_queue.put_nowait({
                            "type": "log",
                            "content": f"[Item {_idx + 1}] Step {step_counter}/{MAX_STEPS}: Processing..."
                        })

                agent = Agent(
                    task=task,
                    llm=llm,
                    browser=browser,
                    tools=local_tools,
                    extend_system_message=extend_system_message,
                    register_new_step_callback=step_callback,
                    max_steps=MAX_STEPS,
                    max_failures=3,
                    max_actions_per_step=4,
                    calculate_cost=True,  # Enable token/cost tracking
                )

                # Run agent for this item
                item_result = None
                item_error = None
                item_usage = None

                async def run_item_agent(_sid=current_session_id, _idx=current_idx):
                    nonlocal item_result, item_error, item_usage
                    try:
                        history = await agent.run()
                        item_result = history.final_result()

                        # Capture usage stats
                        try:
                            usage = history.usage
                            if usage:
                                item_usage = {
                                    "input_tokens": usage.total_prompt_tokens,
                                    "output_tokens": usage.total_completion_tokens,
                                    "total_tokens": usage.total_tokens,
                                    "total_cost": usage.total_cost,
                                    "steps": step_counter
                                }
                                event_queue.put_nowait({
                                    "type": "item_usage",
                                    "content": item_usage,
                                    "batch_item_index": _idx
                                })
                                logger.info(f"[Item {_idx}] Token usage - Input: {usage.total_prompt_tokens}, Output: {usage.total_completion_tokens}, Cost: ${usage.total_cost:.4f}")
                        except Exception as usage_err:
                            logger.warning(f"Could not get usage stats for item {_idx}: {usage_err}")
                            event_queue.put_nowait({
                                "type": "item_usage",
                                "content": {"steps": step_counter},
                                "batch_item_index": _idx
                            })
                    except Exception as e:
                        item_error = str(e)
                    finally:
                        if _sid in _pending_inputs:
                            future = _pending_inputs.pop(_sid)
                            if not future.done():
                                future.cancel()
                        event_queue.put_nowait(None)

                # Start agent task
                asyncio.create_task(run_item_agent())

                # Stream events for this item
                while True:
                    event = await event_queue.get()
                    if event is None:
                        break
                    yield f"data: {json.dumps(event)}\n\n"

                # Update result based on outcome
                if item_error:
                    results[idx].status = "failed"
                    results[idx].error = item_error
                    yield f"data: {json.dumps({'type': 'log', 'content': f'Item {idx + 1} FAILED: {item_error}'})}\n\n"
                else:
                    result_str = str(item_result).lower() if item_result else ""
                    # Check for failure indicators in the result message
                    failure_indicators = [
                        "out of stock", "sold out", "unavailable", "not available",
                        "cannot be completed", "could not be placed", "cannot be placed",
                        "order failed", "unable to order", "product unavailable",
                        "currently unavailable", "no longer available"
                    ]
                    is_actual_failure = any(indicator in result_str for indicator in failure_indicators)

                    if is_actual_failure:
                        results[idx].status = "failed"
                        results[idx].error = str(item_result)
                        yield f"data: {json.dumps({'type': 'log', 'content': f'Item {idx + 1} FAILED: {item_result}'})}\n\n"
                    else:
                        results[idx].status = "success"
                        results[idx].message = str(item_result)
                        yield f"data: {json.dumps({'type': 'log', 'content': f'Item {idx + 1} completed successfully'})}\n\n"

                # Accumulate usage stats
                if item_usage:
                    total_batch_usage["input_tokens"] += item_usage.get("input_tokens", 0)
                    total_batch_usage["output_tokens"] += item_usage.get("output_tokens", 0)
                    total_batch_usage["total_tokens"] += item_usage.get("total_tokens", 0)
                    total_batch_usage["total_cost"] += item_usage.get("total_cost", 0)
                    total_batch_usage["total_steps"] += item_usage.get("steps", 0)

                # Send updated batch status
                yield f"data: {json.dumps({'type': 'batch_status', 'content': [r.model_dump() for r in results]})}\n\n"

            except Exception as e:
                results[idx].status = "failed"
                results[idx].error = str(e)
                yield f"data: {json.dumps({'type': 'log', 'content': f'Item {idx + 1} FAILED: {str(e)}'})}\n\n"
                yield f"data: {json.dumps({'type': 'batch_status', 'content': [r.model_dump() for r in results]})}\n\n"

        # Send final batch complete event
        yield f"data: {json.dumps({'type': 'log', 'content': 'All items processed'})}\n\n"
        success_count = sum(1 for r in results if r.status == "success")
        failed_count = sum(1 for r in results if r.status == "failed")

        # Send total usage stats for the batch
        yield f"data: {json.dumps({'type': 'batch_usage', 'content': total_batch_usage})}\n\n"

        yield f"data: {json.dumps({'type': 'batch_complete', 'content': {'total': len(results), 'success': success_count, 'failed': failed_count, 'results': [r.model_dump() for r in results], 'usage': total_batch_usage}})}\n\n"

    finally:
        # Close browser ONLY after ALL items are processed
        try:
            yield f"data: {json.dumps({'type': 'log', 'content': 'Closing browser after batch completion'})}\n\n"
            await browser.kill()
        except Exception as close_error:
            logger.warning(f"Error closing browser: {close_error}")
