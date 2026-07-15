# services/order_intent_handler.py
"""
Orchestration: per-turn decision logic for order-related intents.
Owns session-state, calls adapter via endpoints, sequences confirm-step
for mutating actions. Sits between chatbot_service.py and the routes.
"""
import re
from typing import Optional
from datetime import datetime, timedelta
from fastapi import HTTPException

from services.shopify_order_adapter import ShopifyOrderAdapter
from services.auth import verify_api_key


# In-memory session store (MVP) — swap to Redis before multi-instance deploy
# Key: session_id, Value: dict (see schema below)
_session_store: dict = {}

SESSION_TTL_MINUTES = 30


def _get_session(session_id: str) -> dict:
    """Load or init session state"""
    if session_id not in _session_store:
        _session_store[session_id] = {
            "order_flow_state": "none",  # none | awaiting_verify | verified | awaiting_confirm
            "verify_token": None,
            "verified_order_id": None,
            "customer_id": None,
            "auth_checked": False,
            "verify_attempts": 0,
            "pending_action": None,  # {action: "cancel"|"return", order_id, payload, expires_at}
            "last_active": datetime.utcnow(),
        }
    
    sess = _session_store[session_id]
    # Touch last_active (in real Redis: just refresh TTL)
    sess["last_active"] = datetime.utcnow()
    return sess


def _cleanup_old_sessions():
    """Periodic cleanup — call from a background task in production"""
    cutoff = datetime.utcnow() - timedelta(minutes=SESSION_TTL_MINUTES)
    expired = [sid for sid, s in _session_store.items() if s.get("last_active", cutoff) < cutoff]
    for sid in expired:
        del _session_store[sid]


# ============================================================
# Public entry points
# ============================================================

async def handle_order_status_query(
    message: str,
    session_id: str,
    product_context: dict,
    x_api_key: str,
) -> dict:
    """
    User asking about an order's status/whereabouts.
    Returns dict: {reply_text, structured_data?, error?}
    """
    sess = _get_session(session_id)
    config = verify_api_key(x_api_key)
    adapter = _build_adapter(config)
    
    # Already verified this session — use cached state
    if sess["order_flow_state"] == "verified" and sess.get("verified_order_id"):
        return await _fetch_and_format(sess["verified_order_id"], sess, x_api_key, adapter)
    
    # Authenticated path — try to silently resolve via customer_id
    if not sess["auth_checked"] and product_context.get("customer_id"):
        sess["auth_checked"] = True
        from services.auth import _call_internal_auth_check  # helper, see below
        auth_result = await _call_internal_auth_check(
            product_context["customer_id"], None, x_api_key
        )
        if auth_result.get("authenticated"):
            sess["customer_id"] = auth_result["customer_id"]
            return await _handle_authenticated_list(sess, adapter, x_api_key)
    
    # Guest path — try to extract order# + email from free text
    extracted = _extract_order_info(message)
    if extracted.get("order_number") and (extracted.get("email") or extracted.get("phone_last4")):
        return await _handle_guest_verify(sess, extracted, x_api_key, adapter)
    
    # Not enough info — ask
    sess["order_flow_state"] = "awaiting_verify"
    return {
        "reply_text": "Sure, I can look that up! Please share your order number and the email (or phone last 4 digits) used at checkout.",
        "next_state": "awaiting_verify",
    }


async def handle_order_cancel(
    message: str,
    session_id: str,
    product_context: dict,
    x_api_key: str,
) -> dict:
    """User wants to cancel an order — needs confirm-step"""
    sess = _get_session(session_id)
    config = verify_api_key(x_api_key)
    adapter = _build_adapter(config)
    
    # If we have a pending cancel waiting for confirm, check user's reply
    if sess.get("pending_action") and sess["pending_action"]["action"] == "cancel":
        if _is_confirmation(message):
            # Execute the cancel
            return await _execute_pending_action(sess, adapter, x_api_key)
        else:
            # User said no — cancel the pending
            sess["pending_action"] = None
            return {"reply_text": "No problem, I won't cancel anything. Anything else I can help with?"}
    
    # Need to identify the order first
    target_order_id = sess.get("verified_order_id")
    if not target_order_id:
        # Try to find it from current message
        extracted = _extract_order_info(message)
        if extracted.get("order_number"):
            verify_result = await _try_guest_verify(sess, extracted, x_api_key, adapter)
            if verify_result.get("verified"):
                target_order_id = verify_result["order_id"]
    
    if not target_order_id:
        return {
            "reply_text": "Which order would you like to cancel? Please provide the order number and email to verify ownership first.",
            "next_state": "awaiting_verify",
        }
    
    # Fetch order to check eligibility
    order = await adapter.get_order(target_order_id)
    if not order:
        return {"reply_text": "I couldn't find that order."}
    
    if not order.cancellable:
        return {
            "reply_text": f"Order #{order.order_number} can't be cancelled because it's already {order.status.value}. If it's been shipped, I can help you with a return instead."
        }
    
    # Build pending action, ask for confirm
    sess["pending_action"] = {
        "action": "cancel",
        "order_id": target_order_id,
        "expires_at": (datetime.utcnow() + timedelta(minutes=5)).isoformat(),
    }
    sess["order_flow_state"] = "awaiting_confirm"
    
    items_summary = ", ".join([item.name for item in order.items[:3]])
    if len(order.items) > 3:
        items_summary += f" and {len(order.items) - 3} more"
    
    return {
        "reply_text": (
            f"I can cancel order #{order.order_number} ({items_summary}, total {order.currency} {order.total:.2f}). "
            f"Refund will be issued to your original payment method in 3-5 business days. "
            f"\n\nShall I proceed? (yes/no)"
        ),
        "next_state": "awaiting_confirm",
    }


async def handle_order_return(
    message: str,
    session_id: str,
    product_context: dict,
    x_api_key: str,
) -> dict:
    """User wants to return an order — needs confirm-step + which items"""
    sess = _get_session(session_id)
    config = verify_api_key(x_api_key)
    adapter = _build_adapter(config)
    
    # Confirm-step for pending return
    if sess.get("pending_action") and sess["pending_action"]["action"] == "return":
        if _is_confirmation(message):
            return await _execute_pending_action(sess, adapter, x_api_key)
        else:
            sess["pending_action"] = None
            return {"reply_text": "Got it, I won't process the return. Anything else?"}
    
    target_order_id = sess.get("verified_order_id")
    if not target_order_id:
        extracted = _extract_order_info(message)
        if extracted.get("order_number"):
            verify_result = await _try_guest_verify(sess, extracted, x_api_key, adapter)
            if verify_result.get("verified"):
                target_order_id = verify_result["order_id"]
    
    if not target_order_id:
        return {
            "reply_text": "Which order would you like to return? Please provide the order number and email first.",
            "next_state": "awaiting_verify",
        }
    
    order = await adapter.get_order(target_order_id)
    if not order:
        return {"reply_text": "I couldn't find that order."}
    
    if not order.returnable:
        return {
            "reply_text": f"Order #{order.order_number} is currently {order.status.value} and not eligible for return yet."
        }
    
    # Store pending return — ask which items + reason
    sess["pending_action"] = {
        "action": "return",
        "order_id": target_order_id,
        "items": [{"sku": item.sku, "name": item.name} for item in order.items if item.sku],
        "expires_at": (datetime.utcnow() + timedelta(minutes=5)).isoformat(),
    }
    
    items_list = "\n".join([f"  • {item.name} (SKU: {item.sku})" for item in order.items if item.sku])
    
    return {
        "reply_text": (
            f"Order #{order.order_number} is eligible for return. Which items would you like to return, "
            f"and what's the reason?\n\n{items_list}\n\n"
            f"Please list the item names and your reason."
        ),
        "next_state": "awaiting_return_details",
    }


# ============================================================
# Internal helpers
# ============================================================

def _build_adapter(config: dict) -> ShopifyOrderAdapter:
    """
    Build Shopify adapter. Falls back to env vars if config doesn't have credentials.
    """
    import os
    
    # Get platform - default to "shopify" since this is your main platform
    platform = config.get("platform") or "shopify"
    
    # Get shop domain - try config first, then env var
    shop_domain = (
        config.get("shop_domain") or 
        config.get("shopify_shop") or 
        os.getenv("SHOPIFY_STORE") or 
        os.getenv("SHOPIFY_SHOP_DOMAIN")
    )
    
    # Get access token - try config first, then env var
    access_token = (
        config.get("shopify_access_token") or 
        config.get("access_token") or 
        os.getenv("SHOPIFY_ACCESS_TOKEN")
    )
    
    # Validate
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
    
    # Only support Shopify for now
    if platform != "shopify":
        raise HTTPException(
            status_code=501, 
            detail=f"Platform '{platform}' not yet supported. Only 'shopify' is implemented."
        )
    
    return ShopifyOrderAdapter(
        shop_domain=shop_domain,
        access_token=access_token,
    )


async def _fetch_and_format(order_id: str, sess: dict, x_api_key: str, adapter) -> dict:
    """Fetch order, return human-friendly summary"""
    order = await adapter.get_order(order_id)
    if not order:
        return {"reply_text": "I couldn't find that order."}
    
    summary = _format_order_summary(order)
    return {"reply_text": summary, "structured_data": order.dict()}


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


async def _handle_authenticated_list(sess: dict, adapter, x_api_key: str) -> dict:
    """Customer is authenticated — list their recent orders"""
    customer_id = sess["customer_id"]
    orders = await adapter.list_orders_by_customer(customer_id, limit=5)
    
    if not orders:
        return {"reply_text": "I don't see any orders on your account."}
    
    if len(orders) == 1:
        # Single order — auto-select
        order_id = orders[0].order_id
        full = await adapter.get_order(order_id)
        if full:
            sess["order_flow_state"] = "verified"
            sess["verified_order_id"] = order_id
            return {
                "reply_text": _format_order_summary(full),
                "structured_data": full.dict(),
            }
    
    # Multiple orders — ask which
    order_list = "\n".join([
        f"  • #{o.order_number} — {o.status.value} — {o.currency} {o.total:.2f} ({o.placed_at})"
        for o in orders
    ])
    return {
        "reply_text": f"Here are your recent orders:\n{order_list}\n\nWhich one are you asking about?",
        "next_state": "awaiting_order_selection",
    }


async def _handle_guest_verify(sess: dict, extracted: dict, x_api_key: str, adapter) -> dict:
    return await _try_guest_verify(sess, extracted, x_api_key, adapter)


async def _try_guest_verify(sess: dict, extracted: dict, x_api_key: str, adapter) -> dict:
    """Try to verify order ownership for guest path"""
    from services.auth import _call_internal_verify
    
    result = await _call_internal_verify(
        order_number=extracted["order_number"],
        email=extracted.get("email"),
        phone_last4=extracted.get("phone_last4"),
        session_id=sess.get("raw_session_id", "anonymous"),
        x_api_key=x_api_key,
    )
    
    if result.get("verified"):
        sess["order_flow_state"] = "verified"
        sess["verify_token"] = result.get("verify_token")
        sess["verified_order_id"] = result.get("order_id")
        sess["verify_attempts"] = 0
        return await _fetch_and_format(result["order_id"], sess, x_api_key, adapter)
    
    sess["verify_attempts"] = sess.get("verify_attempts", 0) + 1
    if sess["verify_attempts"] >= 3:
        return {
            "reply_text": "I'm having trouble verifying your order. For security, I'll connect you with a human agent who can help.",
            "escalate": True,
        }
    
    return {
        "reply_text": result.get("message", "I couldn't verify that order. Please double-check the order number and email.")
    }


async def _execute_pending_action(sess: dict, adapter, x_api_key: str) -> dict:
    """Execute a confirmed pending action (cancel/return)"""
    pending = sess.get("pending_action")
    if not pending:
        return {"reply_text": "I don't have a pending action. What would you like to do?"}
    
    # Check expiry
    expires = datetime.fromisoformat(pending["expires_at"])
    if datetime.utcnow() > expires:
        sess["pending_action"] = None
        return {"reply_text": "That confirmation expired. Please start over."}
    
    if pending["action"] == "cancel":
        result = await adapter.cancel_order(pending["order_id"])
        sess["pending_action"] = None
        sess["order_flow_state"] = "verified"  # still verified, just cancelled now
        
        if result.get("success"):
            return {
                "reply_text": f"Done! Order #{result['order_number']} has been cancelled. {result.get('refund_eta', '')}",
                "structured_data": result,
            }
        return {
            "reply_text": f"I couldn't cancel the order: {result.get('message', 'Unknown error')}",
        }
    
    elif pending["action"] == "return":
        # Should have items + reason from a prior step
        items = [i["sku"] for i in pending.get("items", [])]
        reason = pending.get("reason", "Customer initiated return")
        result = await adapter.create_return(pending["order_id"], items, reason)
        sess["pending_action"] = None
        
        if result.get("success"):
            return {
                "reply_text": f"Return request initiated for order #{result['order_number']}. Reference: {result.get('reference', 'N/A')}. {result.get('refund_eta', '')}",
                "structured_data": result,
            }
        return {
            "reply_text": f"Couldn't initiate return: {result.get('message', 'Unknown error')}",
        }
    
    return {"reply_text": "Unknown pending action."}


# ============================================================
# NLP-lite extraction (regex — swap to LLM function-calling later)
# ============================================================

def _extract_order_info(message: str) -> dict:
    """Pull order# + email or phone from free text"""
    result = {}
    
    # Order number patterns: #1234, 1234, order 1234, ORD-1234
    order_match = re.search(
        r'(?:#|order\s*|ord[-_]?)(\d{3,10})',
        message,
        re.IGNORECASE
    )
    if order_match:
        result["order_number"] = order_match.group(1)
    
    # Email
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', message)
    if email_match:
        result["email"] = email_match.group(0)
    
    # Phone last 4 (pattern: "ends 1234" or "last 4 1234" or just 4 digits in phone context)
    phone_match = re.search(r'(?:last\s*4|ends?\s*(?:in)?)\s*(\d{4})', message, re.IGNORECASE)
    if phone_match:
        result["phone_last4"] = phone_match.group(1)
    
    return result


def _is_confirmation(message: str) -> bool:
    """User said yes/confirm"""
    msg = message.lower().strip()
    return msg in ("yes", "y", "yeah", "yep", "confirm", "ok", "okay", "sure", "proceed", "do it")


# ============================================================
# Public utility — for chatbot_service to call into this
# ============================================================

def reset_session(session_id: str):
    """Wipe session state (e.g., user said 'nevermind' or 'start over')"""
    if session_id in _session_store:
        del _session_store[session_id]