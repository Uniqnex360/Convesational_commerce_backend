import time
import os
from collections import defaultdict
from fastapi import HTTPException
import httpx
import jwt

# ✅ Add Shopify credentials to API key config
API_KEYS = {
    'demo_key_12345': {
        'name': "Demo store",
        "domain": "*",
        "rate_limit": 100,
        "platform": "shopify",  # <-- ADD
        "shop_domain": os.getenv("SHOPIFY_STORE", "rje8b8-na.myshopify.com"),  # <-- ADD
        "shopify_access_token": os.getenv("SHOPIFY_ACCESS_TOKEN"),  # <-- ADD
    }
}

rate_limit_store = defaultdict(list)


def verify_api_key(api_key: str) -> dict:
    if api_key not in API_KEYS:
        raise HTTPException(status_code=401, detail='Invalid API KEY')
    return API_KEYS[api_key]


def get_platform_config(api_key: str) -> dict:
    config = verify_api_key(api_key)
    if "shop_config" not in config:
        raise HTTPException(status_code=500, detail="Platform not configured for this API key")
    return config["shop_config"]


def check_rate_limit(api_key: str, limit: int = 100):
    now = time.time()
    hour_ago = now - 3600
    rate_limit_store[api_key] = [
        req_time for req_time in rate_limit_store[api_key]
        if req_time > hour_ago
    ]
    if len(rate_limit_store[api_key]) >= limit:
        raise HTTPException(status_code=429, detail='Rate limit exceeded')
    rate_limit_store[api_key].append(now)


async def _call_internal_auth_check(customer_id: str, customer_token, x_api_key: str) -> dict:
    """Internal helper — calls our own /orders/auth-check (for orchestration layer)"""
    # For now, trust the customer_id if it's provided
    if customer_id:
        return {"authenticated": True, "customer_id": str(customer_id)}
    return {"authenticated": False}


async def _call_internal_verify(
    order_number: str,
    email: str,
    phone_last4: str,
    session_id: str,
    x_api_key: str,
) -> dict:
    """Internal helper — verify guest order using Shopify API"""
    try:
        shop_domain = os.getenv("SHOPIFY_STORE")
        access_token = os.getenv("SHOPIFY_ACCESS_TOKEN")
        
        if not shop_domain or not access_token:
            return {"verified": False, "message": "Backend not configured"}
        
        # Search for order by order_number
        async with httpx.AsyncClient(timeout=10) as client:
            url = f"https://{shop_domain}/admin/api/2024-01/orders.json?name={order_number}&status=any"
            headers = {"X-Shopify-Access-Token": access_token}
            
            response = await client.get(url, headers=headers)
            
            if response.status_code != 200:
                return {"verified": False, "message": "Order lookup failed"}
            
            data = response.json()
            orders = data.get("orders", [])
            
            if not orders:
                return {"verified": False, "message": "Order not found"}
            
            order = orders[0]
            
            # Verify email
            order_email = order.get("email", "").lower()
            if email and order_email == email.lower():
                return {
                    "verified": True,
                    "order_id": str(order["id"]),
                    "verify_token": _issue_verify_token(str(order["id"]))
                }
            
            # Verify phone last 4
            order_customer = order.get("customer", {})
            order_phone = order_customer.get("phone", "")
            if phone_last4 and order_phone and order_phone[-4:] == phone_last4:
                return {
                    "verified": True,
                    "order_id": str(order["id"]),
                    "verify_token": _issue_verify_token(str(order["id"]))
                }
            
            return {"verified": False, "message": "Order details don't match"}
            
    except Exception as e:
        print(f"Verify error: {e}")
        return {"verified": False, "message": "Verification error"}


def _issue_verify_token(order_id: str) -> str:
    """Issue a short-lived verification token (5 minutes)"""
    secret = os.getenv("VERIFY_TOKEN_SECRET", "change-this-in-production-please")
    payload = {
        "order_id": order_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + 300  # 5 minutes
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def validate_verify_token(token: str) -> dict:
    """Validate a verify token"""
    import jwt
    secret = os.getenv("VERIFY_TOKEN_SECRET", "change-this-in-production-please")
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Verification token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid verification token")