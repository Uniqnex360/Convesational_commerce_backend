# api/v1/endpoints/orders.py
from fastapi import APIRouter, Header, HTTPException
from typing import Optional, List

from models.order_schemas import (
    OrderVerifyRequest, OrderVerifyResponse,
    AuthCheckRequest, AuthCheckResponse,
    OrderContext, OrderListItem,
)
from services.auth import verify_api_key, check_rate_limit
from services.order_auth import (
    check_order_verify_rate_limit,
    verify_customer_token,
    verify_guest_order,
    issue_verify_token,
    validate_verify_token,
)
from services.shopify_order_adapter import ShopifyOrderAdapter

router = APIRouter()


def _get_adapter(config: dict) -> ShopifyOrderAdapter:
   
    if config.get("platform") != "shopify":
        raise HTTPException(status_code=501, detail="Platform not yet supported for order lookup")
    return ShopifyOrderAdapter(
        shop_domain=config["shop_domain"],
        access_token=config["shopify_access_token"],
    )


@router.post("/orders/auth-check", response_model=AuthCheckResponse)
async def auth_check(
    request: AuthCheckRequest,
    x_api_key: str = Header(..., alias="X-API-Key"),
):
   
    config = verify_api_key(x_api_key)
    check_rate_limit(x_api_key, config.get("rate_limit", 100))

    adapter = _get_adapter(config)
    verified_id = await verify_customer_token(
        request.customer_token, request.customer_id, adapter
    )

    return AuthCheckResponse(
        authenticated=verified_id is not None,
        customer_id=verified_id,
    )


@router.post("/orders/verify", response_model=OrderVerifyResponse)
async def verify_order(
    request: OrderVerifyRequest,
    session_id: str = Header(..., alias="X-Session-Id"),
    x_api_key: str = Header(..., alias="X-API-Key"),
):
   
    config = verify_api_key(x_api_key)
    check_order_verify_rate_limit(x_api_key, session_id)  # separate stricter bucket

    if not request.email and not request.phone_last4:
        raise HTTPException(
            status_code=400,
            detail="Provide email or phone (last 4 digits) to verify order ownership",
        )

    adapter = _get_adapter(config)
    order_id = await verify_guest_order(
        request.order_number, request.email, request.phone_last4, adapter
    )

    if not order_id:
        # generic message — never reveal which field mismatched
        return OrderVerifyResponse(
            verified=False,
            message="We couldn't find a matching order. Please double-check your order number and email.",
        )

    token = issue_verify_token(order_id)
    return OrderVerifyResponse(verified=True, order_id=order_id, verify_token=token)


@router.get("/orders/status", response_model=OrderContext)
async def get_order_status(
    order_id: str,
    verify_token: Optional[str] = None,
    customer_id: Optional[str] = None,
    x_api_key: str = Header(..., alias="X-API-Key"),
):
    
    config = verify_api_key(x_api_key)
    check_rate_limit(x_api_key, config.get("rate_limit", 100))

    if not verify_token and not customer_id:
        raise HTTPException(
            status_code=401,
            detail="Order verification required before viewing order details",
        )

    if verify_token:
        payload = validate_verify_token(verify_token)  # raises 401 if expired/invalid
        if payload["order_id"] != order_id:
            raise HTTPException(status_code=403, detail="Verification token does not match this order")

    adapter = _get_adapter(config)
    order = await adapter.get_order(order_id)

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # If customer_id path, confirm this order actually belongs to them
    if customer_id and not verify_token:
        owns_order = await adapter.order_belongs_to_customer(order_id, customer_id)
        if not owns_order:
            raise HTTPException(status_code=403, detail="Order not found")  # generic — don't reveal it exists for someone else

    return order


@router.get("/orders/list", response_model=List[OrderListItem])
async def list_customer_orders(
    customer_id: str,
    x_api_key: str = Header(..., alias="X-API-Key"),
):
  
    config = verify_api_key(x_api_key)
    check_rate_limit(x_api_key, config.get("rate_limit", 100))

    adapter = _get_adapter(config)
    orders = await adapter.list_orders_by_customer(customer_id)
    return orders
@router.post("/orders/cancel", response_model=MutateOrderResponse)
async def cancel_order_endpoint(
    request: CancelOrderRequest,
    verify_token: Optional[str] = Header(None, alias="X-Verify-Token"),
    customer_id: Optional[str] = Header(None, alias="X-Customer-Id"),
    x_api_key: str = Header(..., alias="X-API-Key"),
):
   
    config = verify_api_key(x_api_key)
    check_rate_limit(x_api_key, config.get("rate_limit", 100))
    
    if not verify_token and not customer_id:
        raise HTTPException(status_code=401, detail="Verification required before cancellation")
    
    if verify_token:
        payload = validate_verify_token(verify_token)
        if payload["order_id"] != request.order_id:
            raise HTTPException(status_code=403, detail="Token does not match this order")
    
    adapter = _get_adapter(config)
    
    if customer_id and not verify_token:
        owns = await adapter.order_belongs_to_customer(request.order_id, customer_id)
        if not owns:
            raise HTTPException(status_code=403, detail="Order not found")  # generic
    
    # Idempotency check (TODO: proper idempotency-key in production)
    # For now: rely on Shopify's natural idempotency (cancel-on-cancelled is no-op)
    
    result = await adapter.cancel_order(request.order_id, request.reason)
    
    if not result.get("success"):
        # Map error_code to HTTP status
        code = result.get("error_code", "PLATFORM_ERROR")
        if code == "NOT_ELIGIBLE":
            raise HTTPException(status_code=409, detail=result["message"])  # conflict
        if code == "NOT_FOUND":
            raise HTTPException(status_code=404, detail=result["message"])
        raise HTTPException(status_code=502, detail=result["message"])
    
    return MutateOrderResponse(
        success=True,
        action="cancelled",
        order_id=result["order_id"],
        order_number=result["order_number"],
        new_status=result["new_status"],
        message=f"Order {result['order_number']} has been cancelled.",
        refund_eta=result.get("refund_eta"),
    )


@router.post("/orders/return", response_model=MutateOrderResponse)
async def create_return_endpoint(
    request: ReturnRequestCreate,
    verify_token: Optional[str] = Header(None, alias="X-Verify-Token"),
    customer_id: Optional[str] = Header(None, alias="X-Customer-Id"),
    x_api_key: str = Header(..., alias="X-API-Key"),
):
    
    config = verify_api_key(x_api_key)
    check_rate_limit(x_api_key, config.get("rate_limit", 100))
    
    if not verify_token and not customer_id:
        raise HTTPException(status_code=401, detail="Verification required before return")
    
    if verify_token:
        payload = validate_verify_token(verify_token)
        if payload["order_id"] != request.order_id:
            raise HTTPException(status_code=403, detail="Token does not match this order")
    
    adapter = _get_adapter(config)
    
    if customer_id and not verify_token:
        owns = await adapter.order_belongs_to_customer(request.order_id, customer_id)
        if not owns:
            raise HTTPException(status_code=403, detail="Order not found")
    
    result = await adapter.create_return(
        request.order_id,
        request.item_skus,
        request.reason,
    )
    
    if not result.get("success"):
        code = result.get("error_code", "PLATFORM_ERROR")
        if code == "NOT_ELIGIBLE":
            raise HTTPException(status_code=409, detail=result["message"])
        if code == "NOT_FOUND":
            raise HTTPException(status_code=404, detail=result["message"])
        if code == "INVALID_ITEMS":
            raise HTTPException(status_code=400, detail=result["message"])
        raise HTTPException(status_code=502, detail=result["message"])
    
    return MutateOrderResponse(
        success=True,
        action="return_initiated",
        order_id=result["order_id"],
        order_number=result["order_number"],
        new_status=result["new_status"],
        message=f"Return initiated for order {result['order_number']}.",
        reference=result.get("reference"),
        refund_eta=result.get("refund_eta"),
    )