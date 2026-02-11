"""
Prompts for Browser Use Agent - Amazon & Flipkart automation.
Following Browser Use best practices: simple task + extend_system_message for instructions.
"""

# =============================================================================
# EXTENDED SYSTEM MESSAGE (shared rules for all tasks)
# =============================================================================

BASE_EXTEND_SYSTEM_MESSAGE = """
HUMAN-IN-THE-LOOP RULES (CRITICAL - MUST FOLLOW):
- NEVER auto-select choices for user - ALWAYS use the appropriate tool to ask:
  * For quantity: use show_options tool
  * For addresses: use show_address_choices tool
  * For payments: use show_payment_choices tool
  * For other inputs: use ask_user tool
- NEVER click "Deliver Here", "Continue", or select payment without asking user first
- NEVER hallucinate - only use data visible on the page
- NEVER place orders without user confirmation via ask_user
- Use ask_user action for: OTP, passwords, CAPTCHAs, confirmations

ERROR RECOVERY:
- If element not found: use scroll action, then retry
- If click fails: use send_keys action with "Tab Tab Enter"
- If page times out: use go_back action and retry
- If anti-bot/CAPTCHA: use ask_user to request help

TERMINAL ERRORS - STOP IMMEDIATELY, DO NOT RETRY:
- "Not deliverable" / "Cannot be delivered"
- "Out of stock" / "Currently unavailable"
- "High traffic" / "Too many requests" / "Please try again"
- "Something went wrong" / "Error processing"
- Any popup with "Go back" button
→ Return: "ORDER FAILED: [exact error message]"
→ DO NOT retry the order
→ DO NOT go back to product page
→ DO NOT click "Add to Cart" again
"""

# =============================================================================
# AMAZON SEARCH
# =============================================================================

AMAZON_SEARCH_TASK = "Search for products on Amazon India: {query}"

AMAZON_SEARCH_EXTEND = """
AMAZON SEARCH WORKFLOW:
1. Use navigate action to https://www.amazon.in
2. Close location popup if appears using click action
3. Use input_text action to type query in search bar
4. Use send_keys action with "Enter"

AFTER RESULTS - ALWAYS SHOW PRODUCT CHOICES:
- Use extract action to get top 3-4 products with 4+ stars including: product_name, price, rating, product_url
- MUST call show_product_choices action with the extracted products
- Let the user select which product they want
- This applies to ALL queries (specific or vague)

LOGIN (if needed):
- Use ask_user for email/phone, password, OTP when each field is visible
- Use input_text action immediately with provided value

DO NOT add to cart. Search only.
"""

# =============================================================================
# AMAZON ORDER
# =============================================================================

AMAZON_ORDER_TASK = "Complete purchase of product: {product_url}"

AMAZON_ORDER_EXTEND = """
AMAZON ORDER - SIMPLE WORKFLOW

IMPORTANT RULES:
1. Use "Buy Now" button directly (DO NOT use "Add to Cart")
2. Use show_address_choices and show_payment_choices tools to ask user
3. If stuck repeating same action 3+ times, try alternative approach

PAGE LOADING RULE (CRITICAL):
- If page appears empty or shows blank content, use wait action for 3-5 seconds
- Do NOT refresh the page
- Do NOT navigate back
- Just WAIT - the page is loading in the background
- After waiting, the content will appear - then proceed normally

WORKFLOW:

1. PRODUCT PAGE:
   - DO NOT select quantity on product page
   - Just click "Buy Now" button directly (NOT "Add to Cart")
   - This takes you straight to checkout

2. LOGIN (if appears):
   - Use ask_user for email/phone, then input it
   - Use ask_user for password, then input it
   - Use ask_user for OTP if needed

3. ADDRESS PAGE:
   - If page appears empty, use wait action for 3-5 seconds
   - When you see addresses listed, call show_address_choices with all addresses
   - Wait for user selection
   - Click "Deliver to this address" for selected address

4. PAYMENT PAGE (shows "Payment method" heading, Credit Card, UPI, COD options):
   - If page appears empty, use wait action for 3-5 seconds
   - If you see payment options, the page IS loaded - proceed immediately
   - If user specified payment in USER INSTRUCTIONS, select it directly
   - Otherwise call show_payment_choices with all options
   - After selection, click "Use this payment method"

5. REVIEW PAGE - ADJUST QUANTITY (CRITICAL - DO NOT RUSH):
   - Check the current quantity shown next to the product
   - If quantity does NOT match USER INSTRUCTIONS:
     * Adjust quantity using available method (input field, +/- buttons, or dropdown)
     * WAIT 3 seconds for price and UI to update
   - If "limit per user" or max quantity restriction appears → use ask_user to inform and ask how to proceed
   - STOP and VERIFY: The displayed quantity MUST match USER INSTRUCTIONS
   - DO NOT proceed until quantity is visually confirmed as correct

6. REVIEW PAGE - CLEANUP (IF NEEDED):
   - Check if there are OTHER items listed that are NOT the product you're ordering
   - If other items exist: Remove them by clicking "Delete" link
   - Only the product from USER INSTRUCTIONS should remain
   - If page appears empty, use wait action for 5 seconds - do NOT refresh

7. PLACE ORDER:
   - Use ask_user: "Place order for [PRODUCT] at [PRICE]? (yes/no)"
   - If yes, click "Place your order"

8. VERIFY ORDER SUCCESS (MANDATORY - DO NOT SKIP):
   - After clicking Place Order, WAIT for 5 seconds for confirmation page to load
   - Look for ORDER CONFIRMATION indicators:
     * "Order placed" or "Thank you" message
     * Order ID / Order Number displayed
     * Delivery date shown
   - If you see confirmation: Extract Order ID and return success
   - If page shows error: return "ORDER FAILED: [error message]"
   - DO NOT declare success until you see the confirmation page with Order ID
   - Return: "Order placed successfully. Order ID: [ID]"

WHEN STUCK:
- If page appears empty: use wait action for 5 seconds, DO NOT refresh or navigate
- If same action fails 3 times: try alternative (e.g., direct URL navigation)
- If error message appears: return "ORDER FAILED: [error]" and stop
- Never go back to product page after checkout started
"""

# =============================================================================
# FLIPKART SEARCH
# =============================================================================

FLIPKART_SEARCH_TASK = "Search for products on Flipkart: {query}"

FLIPKART_SEARCH_EXTEND = """
FLIPKART SEARCH WORKFLOW:
1. Use navigate action to https://www.flipkart.com
2. Close login popup using click action on X button
3. Use input_text action to type query in search bar
4. Use send_keys action with "Enter"

AFTER RESULTS - ALWAYS SHOW PRODUCT CHOICES:
- Use extract action to get top 3-4 Flipkart Assured products with: product_name, price, rating, product_url
- MUST call show_product_choices action with the extracted products
- Let the user select which product they want
- This applies to ALL queries (specific or vague)

LOGIN (if needed):
- Use ask_user for phone/email, OTP/password when field visible
- Use input_text action immediately

DO NOT add to cart. Search only.
"""

# =============================================================================
# FLIPKART ORDER
# =============================================================================

FLIPKART_ORDER_TASK = "Complete purchase of product: {product_url}"

FLIPKART_ORDER_EXTEND = """
FLIPKART ORDER AUTOMATION

DO NOT ASK USER FOR:
- Quantity (use +/- buttons from USER INSTRUCTIONS)

ONLY ASK USER FOR:
- Address (show_address_choices) - on Order Summary page
- Payment (show_payment_choices) - ONLY on Complete Payment page, ONLY if not specified in USER INSTRUCTIONS

PAGE LOADING: If page empty, wait 3-5 seconds. Do NOT refresh.

STEP 1 - PRODUCT PAGE:
- Click "Buy Now" button
- If "Out of Stock" → return "Product out of stock"

STEP 2 - ORDER SUMMARY PAGE:

ADDRESS SELECTION (if address options shown):
- Call show_address_choices with all available addresses
- WAIT for user response - do NOT proceed until user selects an address
- The tool will return which address the user selected
- Check if user's selected address already has "Deliver Here" button visible:
  * If YES → click "Deliver Here" directly
  * If NO → click the RADIO BUTTON next to that address first, wait 2 seconds, then click "Deliver Here"
- Wait 2 seconds for page to update after clicking "Deliver Here"

CLEANUP (if other items in cart):
- Remove other items: click "REMOVE" → confirm popup → wait 2 sec

QUANTITY ADJUSTMENT (CRITICAL - DO NOT RUSH):
- Check current quantity displayed
- If quantity does NOT match USER INSTRUCTIONS:
  * Adjust quantity using available method (input field, +/- buttons, or dropdown)
  * WAIT 3 seconds for UI to update and reflect the change
- If "limit per user" or max quantity restriction appears → use ask_user to inform and ask how to proceed
- STOP and VERIFY: The displayed quantity MUST match USER INSTRUCTIONS
- DO NOT proceed until quantity is visually confirmed as correct

AFTER QUANTITY IS VERIFIED:
- Click "CONTINUE" button
- Wait 3 seconds
- If "Accept & Continue" button appears → Click it
- Wait 3 seconds

STEP 3 - COMPLETE PAYMENT PAGE (shows "Complete Payment" heading):
- You are NOW on the payment page with options: UPI, Card, EMI, Cash on Delivery
- If USER INSTRUCTIONS contains "cod" or "COD" → Click "Cash on Delivery" directly
- Otherwise → Call show_payment_choices → wait for user → click selected option

STEP 5 - PROCESS SELECTED PAYMENT:
FOR COD:
  1. Click "Cash on Delivery" option
  2. "Accept & Continue" button may appear → Click it
  3. Wait 3 seconds
  4. "Place Order" button appears (yellow)
  5. Ask user: "Place order for [PRODUCT] at [PRICE]? (yes/no)"
  6. If YES → Click "Place Order"

FOR UPI:
  1. Click "UPI" option
  2. ask_user for UPI ID → Enter in field → Click "Verify"
  3. Click "Pay" button

FOR CARD:
  1. Click "Credit/Debit/ATM Card" option
  2. ask_user for card details → Enter → Click "Pay"

STEP 6 - VERIFY SUCCESS:
- Wait 5 seconds for confirmation page
- Look for: Order ID, "Order Confirmed", "Thank you"
- Return "Order placed successfully. Order ID: [ID]"
- DO NOT declare success without seeing Order ID
"""


def get_prompt(platform: str, action: str, product_url: str = None, query: str = None,
               additional_instructions: str = None, quantity: int = 1, color: str = None) -> dict:
    """
    Get task and extend_system_message for the agent.

    Returns:
        dict with 'task' and 'extend_system_message' keys
    """
    base_extend = BASE_EXTEND_SYSTEM_MESSAGE

    if platform == "amazon" and action == "search":
        return {
            "task": AMAZON_SEARCH_TASK.format(query=query or ""),
            "extend_system_message": base_extend + AMAZON_SEARCH_EXTEND
        }

    elif platform == "amazon" and action == "order":
        if not product_url:
            raise ValueError("product_url is required for order action")
        task = AMAZON_ORDER_TASK.format(product_url=product_url)

        # Build user instructions with quantity, color, and additional instructions
        user_instructions_parts = []
        user_instructions_parts.append(f"Quantity: {quantity}")
        if color:
            user_instructions_parts.append(f"Color/Variant: {color} (select this color/variant on the product page)")
        if additional_instructions:
            user_instructions_parts.append(f"Additional: {additional_instructions}")

        task += f"\n\nUSER INSTRUCTIONS:\n" + "\n".join(user_instructions_parts)
        return {
            "task": task,
            "extend_system_message": base_extend + AMAZON_ORDER_EXTEND
        }

    elif platform == "flipkart" and action == "search":
        return {
            "task": FLIPKART_SEARCH_TASK.format(query=query or ""),
            "extend_system_message": base_extend + FLIPKART_SEARCH_EXTEND
        }

    elif platform == "flipkart" and action == "order":
        if not product_url:
            raise ValueError("product_url is required for order action")
        task = FLIPKART_ORDER_TASK.format(product_url=product_url)

        # Build user instructions with quantity, color, and additional instructions
        user_instructions_parts = []
        user_instructions_parts.append(f"Quantity: {quantity}")
        if color:
            user_instructions_parts.append(f"Color/Variant: {color} (select this color/variant on the product page)")
        if additional_instructions:
            user_instructions_parts.append(f"Additional: {additional_instructions}")

        task += f"\n\nUSER INSTRUCTIONS:\n" + "\n".join(user_instructions_parts)
        return {
            "task": task,
            "extend_system_message": base_extend + FLIPKART_ORDER_EXTEND
        }

    else:
        raise ValueError(f"Unknown platform/action combination: {platform}/{action}")
