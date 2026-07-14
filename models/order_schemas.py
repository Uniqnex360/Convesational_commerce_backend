from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Literal
from enum import Enum
from datetime import datetime


# ============================================================
# ENUMS - MUST be defined FIRST
# ============================================================
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


# ============================================================
# SUB-MODELS
# ============================================================
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


# ============================================================
# MAIN MODELS - Now safe to use OrderStatus
# ============================================================
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


class OrderListItem(BaseModel):
    order_id: str
    order_number: str
    status: OrderStatus
    placed_at: Optional[datetime] = None
    total: Optional[float] = None
    currency: Optional[str] = None


# ============================================================
# REQUEST/RESPONSE MODELS
# ============================================================
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


class CancelOrderRequest(BaseModel):
    order_id: str
    reason: Optional[str] = Field(default=None, max_length=500)
    confirmation: Literal["yes", "confirm"]


class ReturnRequestCreate(BaseModel):
    order_id: str
    item_skus: List[str] = Field(..., min_items=1)
    reason: str = Field(..., min_length=3, max_length=500)
    confirmation: Literal["yes", "confirm"]


class MutateOrderResponse(BaseModel):
    success: bool
    action: str
    order_id: str
    order_number: str
    new_status: OrderStatus
    message: str
    refund_eta: Optional[str] = None
    reference: Optional[str] = None
