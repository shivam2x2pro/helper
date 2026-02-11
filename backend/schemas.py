from pydantic import BaseModel
from typing import Optional, Literal, Dict, Any, List

class AgentRequest(BaseModel):
    platform: Literal["amazon", "flipkart"]
    action: Literal["search", "order", "chat"]
    user_message: str
    product_url: Optional[str] = None
    quantity: Optional[int] = 1  # Quantity for order action
    color: Optional[str] = None  # Color variant for order action
    session_id: Optional[str] = None # To resume or identify session
    temperature: Optional[float] = None  # LLM temperature (0.0 = deterministic, 1.0 = creative)

class BatchOrderItem(BaseModel):
    product_url: str
    quantity: int = 1
    color: Optional[str] = None  # Optional color variant

class BatchOrderRequest(BaseModel):
    platform: Literal["amazon", "flipkart"]
    items: List[BatchOrderItem]
    additional_instructions: Optional[str] = None
    session_id: Optional[str] = None
    temperature: Optional[float] = None

class UserInputRequest(BaseModel):
    session_id: str
    input_data: str # JSON string or plain text

class AgentResponse(BaseModel):
    # This might not be used directly if we stream, but good for final result
    status: str
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

class BatchItemResult(BaseModel):
    index: int
    product_url: str
    quantity: int
    color: Optional[str] = None
    status: Literal["pending", "in_progress", "success", "failed"]
    message: Optional[str] = None
    error: Optional[str] = None
