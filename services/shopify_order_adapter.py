import os
import httpx
from typing import Optional, List
from datetime import datetime
from models.order_schemas import (
    OrderContext, OrderLineItem, TrackingInfo, MaskedCustomer,
    OrderStatus, OrderListItem
)
SHOPIFY_API_VERSION = "2024-10"  
def _mask_email(email: Optional[str]) -> Optional[str]:
    if not email or "@" not in email:
        return None
    name, domain = email.split("@", 1)
    if len(name) <= 2:
        masked = name[0] + "*"
    else:
        masked = name[0] + "*" * (len(name) - 2) + name[-1]
    return f"{masked}@{domain}"
def _mask_phone(phone: Optional[str]) -> Optional[str]:
    if not phone or len(phone) < 4:
        return None
    return "*" * (len(phone) - 4) + phone[-4:]
def _map_shopify_status(order: dict) -> OrderStatus:
    if order.get("cancelled_at"):
        return OrderStatus.cancelled
    financial = order.get("financial_status")
    if financial == "refunded":
        return OrderStatus.refunded
    if financial == "partially_refunded":
        return OrderStatus.partially_refunded
    fulfillment = order.get("fulfillment_status")
    if fulfillment == "fulfilled":
        return OrderStatus.delivered  
    if fulfillment == "partial":
        return OrderStatus.partially_shipped
    if fulfillment is None:
        return OrderStatus.processing
    return OrderStatus.placed
def _normalize_order(order: dict) -> OrderContext:
    line_items = []
    for li in order.get("line_items", []):
        line_items.append(OrderLineItem(
            sku=li.get("sku"),
            name=li.get("name") or li.get("title", "Item"),
            quantity=li.get("quantity", 1),
            line_status=_map_shopify_status(order),  
            price=float(li.get("price", 0)) if li.get("price") else None,
        ))
    fulfillments = order.get("fulfillments", [])
    tracking = None
    if fulfillments:
        f = fulfillments[0]  
        tracking = TrackingInfo(
            carrier=f.get("tracking_company"),
            tracking_number=f.get("tracking_number"),
            tracking_url=f.get("tracking_url"),
            eta=None,  
        )
    customer = order.get("customer") or {}
    masked_customer = MaskedCustomer(
        masked_email=_mask_email(order.get("email") or customer.get("email")),
        masked_phone=_mask_phone(order.get("phone") or customer.get("phone")),
    )
    status = _map_shopify_status(order)
    return OrderContext(
        order_id=str(order["id"]),
        order_number=str(order.get("name", "")).lstrip("
        status=status,
        items=line_items,
        tracking=tracking,
        customer=masked_customer,
        total=float(order.get("total_price", 0)) if order.get("total_price") else None,
        currency=order.get("currency"),
        placed_at=order.get("created_at"),
        updated_at=order.get("updated_at"),
        cancellable=(status in (OrderStatus.placed, OrderStatus.processing)),
        returnable=(status == OrderStatus.delivered),
    )
class ShopifyOrderAdapter:
    def __init__(self, shop_domain: str, access_token: str):
        self.shop_domain = shop_domain
        self.access_token = access_token
        self.base_url = f"https://{shop_domain}/admin/api/{SHOPIFY_API_VERSION}"
    def _headers(self):
        return {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json",
        }
    async def match_order(self, order_number: str, email: Optional[str], phone_last4: Optional[str]) -> Optional[str]:
        clean_number = order_number.lstrip("
        url = f"{self.base_url}/orders.json"
        params = {"name": f"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=self._headers(), params=params)
            resp.raise_for_status()
            orders = resp.json().get("orders", [])
        if not orders:
            return None
        order = orders[0]
        order_email = (order.get("email") or "").strip().lower()
        order_phone = (order.get("phone") or order.get("customer", {}).get("phone") or "")
        if email and order_email == email.strip().lower():
            return str(order["id"])
        if phone_last4 and order_phone.endswith(phone_last4):
            return str(order["id"])
        return None 
    async def order_belongs_to_customer(self, order_id: str, customer_id: str) -> bool:
        url = f"{self.base_url}/orders/{order_id}.json"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=self._headers())
            if resp.status_code == 404:
                return False
            resp.raise_for_status()
            order = resp.json().get("order")
        if not order:
            return False
        order_customer = order.get("customer") or {}
        return str(order_customer.get("id", "")) == str(customer_id)
    async def get_order(self, order_id: str) -> Optional[OrderContext]:
        url = f"{self.base_url}/orders/{order_id}.json"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=self._headers())
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            order = resp.json().get("order")
        if not order:
            return None
        return _normalize_order(order)
async def cancel_order(self, order_id: str, reason: Optional[str] = None) -> dict:
    url = f"{self.base_url}/orders/{order_id}/cancel.json"
    payload = {}
    if reason:
        payload["reason"] = reason
    payload["email"] = True  
    payload["refund"] = True  
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(url, headers=self._headers(), json=payload)
        if resp.status_code == 422:
            error_body = resp.json() if resp.text else {}
            return {
                "success": False,
                "error_code": "NOT_ELIGIBLE",
                "message": "This order can no longer be cancelled.",
            }
        if resp.status_code == 404:
            return {
                "success": False,
                "error_code": "NOT_FOUND",
                "message": "Order not found.",
            }
        if resp.status_code >= 400:
            return {
                "success": False,
                "error_code": "PLATFORM_ERROR",
                "message": "Unable to cancel the order right now. Please try again later.",
            }
        resp.raise_for_status()
        order = resp.json().get("order", {})
        return {
            "success": True,
            "action": "cancelled",
            "order_id": str(order.get("id", order_id)),
            "order_number": str(order.get("order_number", order.get("name", ""))),
            "new_status": _map_shopify_status(order),
            "refund_eta": "3-5 business days",
        }
    async def create_return(self, order_id: str, item_skus: List[str], reason: str) -> dict:
        order = await self.get_order(order_id)
        if not order:
            return {
                "success": False,
                "error_code": "NOT_FOUND",
                "message": "Order not found.",
            }
        if not order.returnable:
            return {
                "success": False,
                "error_code": "NOT_ELIGIBLE",
                "message": "This order is not eligible for return at this time.",
            }
        order_skus = {item.sku for item in order.items if item.sku}
        invalid_skus = [s for s in item_skus if s not in order_skus]
        if invalid_skus:
            return {
                "success": False,
                "error_code": "INVALID_ITEMS",
                "message": "One or more items are not part of this order.",
            }
        import secrets
        reference = f"RET-{secrets.token_hex(4).upper()}"
        return {
            "success": True,
            "action": "return_initiated",
            "order_id": order_id,
            "order_number": order.order_number,
            "new_status": order.status,  
            "reference": reference,
            "refund_eta": "5-7 business days after we receive your items",
        }
    async def list_orders_by_customer(self, customer_id: str, limit: int = 10) -> List[OrderListItem]:
        url = f"{self.base_url}/customers/{customer_id}/orders.json"
        params = {"limit": limit, "status": "any"}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=self._headers(), params=params)
            resp.raise_for_status()
            orders = resp.json().get("orders", [])
        return [
            OrderListItem(
                order_id=str(o["id"]),
                order_number=str(o.get("name", "")).lstrip("
                status=_map_shopify_status(o),
                placed_at=o.get("created_at"),
                total=float(o.get("total_price", 0)) if o.get("total_price") else None,
                currency=o.get("currency"),
            )
            for o in orders
        ]
    async def verify_customer(self, customer_token: Optional[str], customer_id: Optional[str]) -> Optional[str]:
      
        if not customer_id:
            return None
        url = f"{self.base_url}/customers/{customer_id}.json"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=self._headers())
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            customer = resp.json().get("customer")
        return str(customer["id"]) if customer else None