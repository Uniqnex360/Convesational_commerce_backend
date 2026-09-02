
import re
from typing import Optional
from datetime import datetime, timedelta
from fastapi import HTTPException

from services.shopify_order_adapter import ShopifyOrderAdapter
from services.auth import verify_api_key
import os
import httpx

USE_MOCK = os.getenv("USE_MOCK_ORDERS", "true").lower() == "true"
MOCK_API_URL = os.getenv("API_BASE_URL", "https://convesational-commerce-backend.onrender.com")


_session_store: dict = {}

SESSION_TTL_MINUTES = 30


def _get_session(session_id: str) -> dict:
    if session_id not in _session_store:
        _session_store[session_id] = {
            "order_flow_state": "none", 
            "verify_token": None,
            "verified_order_id": None,
            "customer_id": None,
            "auth_checked": False,
            "verify_attempts": 0,
            "pending_action": None, 
            "last_active": datetime.utcnow(),
        }
    
    sess = _session_store[session_id]
    sess["last_active"] = datetime.utcnow()
    return sess



def _build_adapter(config: dict) -> ShopifyOrderAdapter:
   
    import os
    
    platform = config.get("platform") or "shopify"
    
    shop_domain = (
        config.get("shop_domain") or 
        config.get("shopify_shop") or 
        os.getenv("SHOPIFY_STORE") or 
        os.getenv("SHOPIFY_SHOP_DOMAIN")
    )
    
    access_token = (
        config.get("shopify_access_token") or 
        config.get("access_token") or 
        os.getenv("SHOPIFY_ACCESS_TOKEN")
    )
    
    if not shop_domain:
        raise HTTPException(
            status_code=500, 
            detail="Shop domain not configured. Set SHOPIFY_STORE env var or include shop_domain in config."
        )
    
    if not access_token:
        raise HTTPException(
            status_code=500,
            detail="Shopify access token not configured. Set SHOPIFY_ACCESS_TOKEN env var or include shopify_access_token in config."
        )
    
    if platform != "shopify":
        raise HTTPException(
            status_code=501, 
            detail=f"Platform '{platform}' not yet supported. Only 'shopify' is implemented."
        )
    
    return ShopifyOrderAdapter(
        shop_domain=shop_domain,
        access_token=access_token,
    )



def _format_order_summary(order) -> str:
    parts = [f"Order #{order.order_number} — status: **{order.status.value}**"]
    
    if order.tracking and order.tracking.tracking_number:
        parts.append(f"Tracking: {order.tracking.carrier or 'Carrier'} {order.tracking.tracking_number}")
        if order.tracking.tracking_url:
            parts.append(f"Track at: {order.tracking.tracking_url}")
    
    parts.append(f"Total: {order.currency} {order.total:.2f}")
    
    if order.cancellable:
        parts.append("This order can still be cancelled if needed.")
    elif order.returnable:
        parts.append("This order is eligible for return.")
    
    return "\n".join(parts)


def _extract_order_info(message: str) -> dict:
    result = {}
    
    order_match = re.search(
        r'(?:#|order\s*|ord[-_]?)(\d{3,10})',
        message,
        re.IGNORECASE
    )
    if order_match:
        result["order_number"] = order_match.group(1)
    
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', message)
    if email_match:
        result["email"] = email_match.group(0)
    
    phone_match = re.search(r'(?:last\s*4|ends?\s*(?:in)?)\s*(\d{4})', message, re.IGNORECASE)
    if phone_match:
        result["phone_last4"] = phone_match.group(1)
    
    return result


def _is_confirmation(message: str) -> bool:
    msg = message.lower().strip()
    return msg in ("yes", "y", "yeah", "yep", "confirm", "ok", "okay", "sure", "proceed", "do it")


def reset_session(session_id: str):
    if session_id in _session_store:
        del _session_store[session_id]


async def _fetch_order_mock(order_id: str) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            f"{MOCK_API_URL}/api/v1/mock/orders/status",
            params={"order_id": order_id},
            headers={"X-API-Key": "demo_key_12345"}
        )
        if response.status_code == 200:
            return response.json()
        return None


async def _list_orders_mock(customer_id: str) -> list:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            f"{MOCK_API_URL}/api/v1/mock/orders/list",
            params={"customer_id": customer_id},
            headers={"X-API-Key": "demo_key_12345"}
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("orders", [])
        return []


async def _cancel_order_mock(order_id: str) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            f"{MOCK_API_URL}/api/v1/mock/orders/cancel",
            json={"order_id": order_id, "reason": "customer"},
            headers={"X-API-Key": "demo_key_12345"}
        )
        return response.json()
async def handle_order_status_query(
    message: str,
    session_id: str,
    product_context: dict,
    x_api_key: str,
) -> dict:
   
    sess = _get_session(session_id)
    
    extracted = _extract_order_info(message)
    
    if extracted.get("order_number"):
        order_id = extracted["order_number"]
        
        if USE_MOCK:
            order = await _fetch_order_mock(order_id)
            if order:
                sess["order_flow_state"] = "verified"
                sess["verified_order_id"] = order_id
                return {
                    "reply_text": _format_mock_order(order),
                    "structured_data": order,
                    "next_state": "verified"
                }
            else:
                return {
                    "reply_text": f"I couldn't find order #{order_id}. Please check the order number and try again.",
                    "next_state": "awaiting_verify"
                }
        else:
            try:
                config = verify_api_key(x_api_key)
                adapter = _build_adapter(config)
                order = await adapter.get_order(order_id)
                if order:
                    sess["order_flow_state"] = "verified"
                    sess["verified_order_id"] = order_id
                    return {
                        "reply_text": _format_order_summary(order),
                        "structured_data": order.dict(),
                        "next_state": "verified"
                    }
            except Exception as e:
                print(f"Shopify error, falling back to mock: {e}")
                order = await _fetch_order_mock(order_id)
                if order:
                    return {
                        "reply_text": _format_mock_order(order),
                        "structured_data": order,
                    }
    
    if product_context.get("customer_id") or sess.get("customer_id"):
        customer_id = sess.get("customer_id") or product_context.get("customer_id")
        
        if USE_MOCK:
            orders = await _list_orders_mock(customer_id)
        else:
            try:
                config = verify_api_key(x_api_key)
                adapter = _build_adapter(config)
                orders = await adapter.list_orders_by_customer(customer_id, limit=5)
            except:
                orders = await _list_orders_mock(customer_id)
        
        if not orders:
            return {
                "reply_text": "I don't see any orders on your account.",
                "next_state": "no_orders"
            }
        
        order_list = "\n".join([
            f"{i+1}. Order #{o['order_number']} - {o['status'].upper()} - ${o['total']}"
            for i, o in enumerate(orders[:5])
        ])
        
        return {
            "reply_text": f"Here are your recent orders:\n\n{order_list}\n\nPlease provide the order number you'd like to know more about.",
            "next_state": "awaiting_order_selection"
        }
    
    return {
        "reply_text": "Please provide your order number and the email (or phone last 4 digits) used at checkout.",
        "next_state": "awaiting_verify"
    }


async def handle_order_cancel(
    message: str,
    session_id: str,
    product_context: dict,
    x_api_key: str,
) -> dict:
    sess = _get_session(session_id)
    extracted = _extract_order_info(message)
    
    target_order_id = extracted.get("order_number") or sess.get("verified_order_id")
    
    if not target_order_id:
        return {
            "reply_text": "Which order would you like to cancel? Please provide the order number.",
            "next_state": "awaiting_order_number"
        }
    
    if USE_MOCK:
        order = await _fetch_order_mock(target_order_id)
    else:
        try:
            config = verify_api_key(x_api_key)
            adapter = _build_adapter(config)
            order = await adapter.get_order(target_order_id)
        except:
            order = await _fetch_order_mock(target_order_id)
    
    if not order:
        return {"reply_text": f"I couldn't find order #{target_order_id}."}
    
    if not order.get("cancellable"):
        return {
            "reply_text": f"Order #{order['order_number']} cannot be cancelled (status: {order['status']}). If it has shipped, I can help with a return instead."
        }
    
    if sess.get("pending_action") and sess["pending_action"].get("action") == "cancel":
        if _is_confirmation(message):
            if USE_MOCK:
                result = await _cancel_order_mock(target_order_id)
            else:
                result = await adapter.cancel_order(target_order_id, "customer")
            
            sess["pending_action"] = None
            
            if result.get("success"):
                return {
                    "reply_text": f"Order #{result['order_number']} has been cancelled. Refund of ${order['total']} will be processed in {result.get('refund_eta', '5-10 business days')}.",
                    "structured_data": result
                }
            return {"reply_text": f"Could not cancel: {result.get('message', 'Unknown error')}"}
        else:
            sess["pending_action"] = None
            return {"reply_text": "No problem, I won't cancel anything. Anything else?"}
    
    sess["pending_action"] = {
        "action": "cancel",
        "order_id": target_order_id,
        "expires_at": (datetime.utcnow() + timedelta(minutes=5)).isoformat()
    }
    
    items_summary = ", ".join([item['name'] for item in order.get('line_items', [])[:3]])
    
    return {
        "reply_text": (
            f"I can cancel order #{order['order_number']} ({items_summary}, total ${order['total']}). "
            f"Refund will be processed in 5-10 business days. "
            f"Shall I proceed? (yes/no)"
        ),
        "next_state": "awaiting_confirm"
    }


async def handle_order_return(
    message: str,
    session_id: str,
    product_context: dict,
    x_api_key: str,
) -> dict:
    sess = _get_session(session_id)
    extracted = _extract_order_info(message)
    
    target_order_id = extracted.get("order_number") or sess.get("verified_order_id")
    
    if not target_order_id:
        return {
            "reply_text": "Which order would you like to return? Please provide the order number.",
            "next_state": "awaiting_order_number"
        }
    
    if USE_MOCK:
        order = await _fetch_order_mock(target_order_id)
    else:
        try:
            config = verify_api_key(x_api_key)
            adapter = _build_adapter(config)
            order = await adapter.get_order(target_order_id)
        except:
            order = await _fetch_order_mock(target_order_id)
    
    if not order:
        return {"reply_text": f"I couldn't find order #{target_order_id}."}
    
    if not order.get("returnable"):
        return {
            "reply_text": f"Order #{order['order_number']} is not eligible for return (status: {order['status']})."
        }
    
    if sess.get("pending_action") and sess["pending_action"].get("action") == "return":
        if _is_confirmation(message):
            items = [item['sku'] for item in order.get('line_items', []) if item.get('sku')]
            
            if USE_MOCK:
                result = await _create_return_mock(target_order_id, items, "Customer initiated return")
            else:
                result = await adapter.create_return(target_order_id, items, "Customer initiated return")
            
            sess["pending_action"] = None
            
            if result.get("success"):
                return {
                    "reply_text": f"Return initiated for order #{result['order_number']}. Reference: {result.get('reference', 'N/A')}. Refund in {result.get('refund_eta', '5-10 business days')}.",
                    "structured_data": result
                }
            return {"reply_text": f"Could not initiate return: {result.get('message', 'Unknown error')}"}
        else:
            sess["pending_action"] = None
            return {"reply_text": "Got it, I won't process the return. Anything else?"}
    
    sess["pending_action"] = {
        "action": "return",
        "order_id": target_order_id,
        "expires_at": (datetime.utcnow() + timedelta(minutes=5)).isoformat()
    }
    
    items_list = "\n".join([f"- {item['name']} (SKU: {item['sku']})" for item in order.get('line_items', []) if item.get('sku')])
    
    return {
        "reply_text": (
            f"Order #{order['order_number']} is eligible for return. Which items would you like to return?\n\n"
            f"{items_list}\n\n"
            f"Shall I initiate return for all items? (yes/no)"
        ),
        "next_state": "awaiting_confirm"
    }

async def _create_return_mock(order_id: str, item_skus: list, reason: str) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            f"{MOCK_API_URL}/api/v1/mock/orders/return",
            json={"order_id": order_id, "item_skus": item_skus, "reason": reason},
            headers={"X-API-Key": "demo_key_12345"}
        )
        return response.json()


def _format_mock_order(order: dict) -> str:
    text = f"Order #{order['order_number']}\n"
    text += f"Status: {order['status'].upper()}\n"
    text += f"Total: ${order['total']} {order['currency']}\n"
    text += f"Date: {order['created_at'].split('T')[0]}\n"
    
    if order.get('tracking') and order['tracking'].get('tracking_url'):
        text += f"Tracking: {order['tracking']['carrier']} {order['tracking']['tracking_number']}\n"
        text += f"Link: {order['tracking']['tracking_url']}\n"
    
    text += "\nItems:\n"
    for item in order.get('line_items', []):
        text += f"- {item['name']} (Qty: {item['quantity']}) - ${item['price']}\n"
        if item.get('product_url'):
            text += f"  View: {item['product_url']}\n"
        if item.get('fulfillment_status') == 'fulfilled':
            text += f"  Status: Shipped\n"
        elif item.get('fulfillment_status') is None:
            text += f"  Status: Pending\n"
    
    if order.get('cancellable'):
        text += "\nThis order can be cancelled."
    elif order.get('returnable'):
        text += "\nThis order is eligible for return."
    
    return text