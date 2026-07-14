from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List,Literal
from enum import Enum
from datetime import datetime
from backend.models.order_schemas import OrderStatus

class OrderListItem(BaseModel):
    order_id: str
    order_number: str
    status: OrderStatus
    placed_at: Optional[datetime] = None
    total: Optional[float] = None
    currency: Optional[str] = None


class CancelOrderRequest(BaseModel):
    order_id: str
    reason: Optional[str] = Field(default=None, max_length=500)
    confirmation: Literal["yes", "confirm"]  # must explicitly type "yes" or "confirm"


class ReturnRequestCreate(BaseModel):
    order_id: str
    item_skus: List[str] = Field(..., min_items=1)
    reason: str = Field(..., min_length=3, max_length=500)
    confirmation: Literal["yes", "confirm"]


class MutateOrderResponse(BaseModel):
    success: bool
    action: str  # "cancelled" | "return_initiated"
    order_id: str
    order_number: str
    new_status: OrderStatus
    message: str
    refund_eta: Optional[str] = None  # human-readable: "3-5 business days"
    reference: Optional[str] = None   # return tracking number, refund id, etc.


class OrderActionError(BaseModel):
    """Structured error response for action failures"""
    success: bool = False
    error_code: str  # NOT_ELIGIBLE, NOT_VERIFIED, ALREADY_CANCELLED, PLATFORM_ERROR
    message: str  # safe, generic — no internal details

class OrderStatus(str, Enum):
    placed = "placed"
    processing = "processing"
    shipped = "shipped"
    partially_shipped = "partially_shipped"
    out_for_delivery = "out_for_delivery"
    delivered = "delivered"
    cancelled = "cancelled"
    refunded = "refunded"
    partially_refunded = "partially_refunded"


class OrderLineItem(BaseModel):
    sku: Optional[str] = None
    name: str
    quantity: int
    line_status: OrderStatus
    price: Optional[float] = None


class TrackingInfo(BaseModel):
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    tracking_url: Optional[str] = None
    eta: Optional[datetime] = None


class MaskedCustomer(BaseModel):
    masked_email: Optional[str] = None
    masked_phone: Optional[str] = None


class OrderContext(BaseModel):
    order_id: str
    order_number: str
    status: OrderStatus
    items: List[OrderLineItem] = []
    tracking: Optional[TrackingInfo] = None
    customer: Optional[MaskedCustomer] = None
    total: Optional[float] = None
    currency: Optional[str] = None
    placed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    cancellable: bool = False
    returnable: bool = False


class OrderVerifyRequest(BaseModel):
    order_number: str
    email: Optional[EmailStr] = None
    phone_last4: Optional[str] = Field(default=None, min_length=4, max_length=4)


class OrderVerifyResponse(BaseModel):
    verified: bool
    order_id: Optional[str] = None
    verify_token: Optional[str] = None
    message: Optional[str] = None


class AuthCheckRequest(BaseModel):
    customer_token: Optional[str] = None
    customer_id: Optional[str] = None


class AuthCheckResponse(BaseModel):
    authenticated: bool
    customer_id: Optional[str] = None
