from fastapi import APIRouter, Header, HTTPException
from typing import Optional, List
import time
import random
import os
import httpx

router = APIRouter()

# ============================================================
# MOCK PRODUCT CATALOG (linked to real products)
# ============================================================

MOCK_PRODUCTS = {
    "WBH-001": {
        "sku": "WBH-001",
        "title": "Wireless Bluetooth Headphones",
        "price": "79.99",
        "image_url": "https://cdn.shopify.com/s/files/1/0913/287/8904/products/wireless-headphones.jpg",
        "handle": "wireless-bluetooth-headphones",
        "product_id": "9001",
        "vendor": "TechBrand",
        "category": "Electronics",
        "in_stock": True,
        "tags": ["wireless", "audio", "bluetooth"]
    },
    "USB-C-6FT": {
        "sku": "USB-C-6FT",
        "title": "USB-C Charging Cable (6ft)",
        "price": "14.99",
        "image_url": "https://cdn.shopify.com/s/files/1/0913/287/8904/products/usb-c-cable.jpg",
        "handle": "usb-c-charging-cable-6ft",
        "product_id": "9002",
        "vendor": "TechBrand",
        "category": "Accessories",
        "in_stock": True,
        "tags": ["cable", "usb-c", "charging"]
    },
    "CASE-CLR": {
        "sku": "CASE-CLR",
        "title": "Phone Case - Clear",
        "price": "19.99",
        "image_url": "https://cdn.shopify.com/s/files/1/0913/287/8904/products/phone-case-clear.jpg",
        "handle": "phone-case-clear",
        "product_id": "9003",
        "vendor": "TechBrand",
        "category": "Accessories",
        "in_stock": True,
        "tags": ["phone", "case", "clear"]
    },
    "LAPTOP-STAND-ALU": {
        "sku": "LAPTOP-STAND-ALU",
        "title": "Laptop Stand - Aluminum",
        "price": "89.99",
        "image_url": "https://cdn.shopify.com/s/files/1/0913/287/8904/products/laptop-stand.jpg",
        "handle": "laptop-stand-aluminum",
        "product_id": "9004",
        "vendor": "TechBrand",
        "category": "Office",
        "in_stock": True,
        "tags": ["laptop", "stand", "aluminum"]
    },
    "KEYB-MECH-RGB": {
        "sku": "KEYB-MECH-RGB",
        "title": "Mechanical Keyboard - RGB",
        "price": "149.99",
        "image_url": "https://cdn.shopify.com/s/files/1/0913/287/8904/products/mech-keyboard.jpg",
        "handle": "mechanical-keyboard-rgb",
        "product_id": "9005",
        "vendor": "TechBrand",
        "category": "Electronics",
        "in_stock": True,
        "tags": ["keyboard", "mechanical", "rgb"]
    },
    "MOUSEPAD-LG": {
        "sku": "MOUSEPAD-LG",
        "title": "Mouse Pad - Large",
        "price": "29.99",
        "image_url": "https://cdn.shopify.com/s/files/1/0913/287/8904/products/mousepad.jpg",
        "handle": "mouse-pad-large",
        "product_id": "9006",
        "vendor": "TechBrand",
        "category": "Office",
        "in_stock": True,
        "tags": ["mousepad", "desk", "office"]
    },
    "USBHUB-7": {
        "sku": "USBHUB-7",
        "title": "USB Hub - 7 Port",
        "price": "19.99",
        "image_url": "https://cdn.shopify.com/s/files/1/0913/287/8904/products/usb-hub.jpg",
        "handle": "usb-hub-7-port",
        "product_id": "9007",
        "vendor": "TechBrand",
        "category": "Electronics",
        "in_stock": True,
        "tags": ["usb", "hub", "7-port"]
    },
    "CHRG-FAST": {
        "sku": "CHRG-FAST",
        "title": "Phone Charger - Fast Charge",
        "price": "29.99",
        "image_url": "https://cdn.shopify.com/s/files/1/0913/287/8904/products/charger.jpg",
        "handle": "phone-charger-fast-charge",
        "product_id": "9008",
        "vendor": "TechBrand",
        "category": "Accessories",
        "in_stock": True,
        "tags": ["charger", "fast-charge", "phone"]
    },
    "SCRN-PROT-TG": {
        "sku": "SCRN-PROT-TG",
        "title": "Screen Protector - Tempered Glass",
        "price": "9.99",
        "image_url": "https://cdn.shopify.com/s/files/1/0913/287/8904/products/screen-protector.jpg",
        "handle": "screen-protector-tempered-glass",
        "product_id": "9009",
        "vendor": "TechBrand",
        "category": "Accessories",
        "in_stock": True,
        "tags": ["screen-protector", "tempered-glass", "phone"]
    },
    "DESK-LAMP-LED": {
        "sku": "DESK-LAMP-LED",
        "title": "Desk Lamp - LED",
        "price": "89.99",
        "image_url": "https://cdn.shopify.com/s/files/1/0913/287/8904/products/desk-lamp.jpg",
        "handle": "desk-lamp-led",
        "product_id": "9010",
        "vendor": "TechBrand",
        "category": "Office",
        "in_stock": True,
        "tags": ["desk", "lamp", "led"]
    }
}


def _enrich_line_items_with_products(line_items: List[dict]) -> List[dict]:
    """Add product details to each line item"""
    enriched = []
    for item in line_items:
        sku = item.get("sku", "")
        product = MOCK_PRODUCTS.get(sku)
        
        enriched_item = {
            **item,
            "product_url": f"https://rje8b8-na.myshopify.com/products/{product['handle']}" if product else None,
            "image_url": product["image_url"] if product else None,
            "vendor": product["vendor"] if product else None,
            "category": product["category"] if product else None,
            "in_stock": product["in_stock"] if product else None,
            "tags": product["tags"] if product else None,
            "can_reorder": product is not None and product.get("in_stock", False),
            "similar_products": _get_similar_products(sku) if product else []
        }
        enriched.append(enriched_item)
    
    return enriched


def _get_similar_products(sku: str) -> List[dict]:
    """Get similar products for re-ordering"""
    if sku not in MOCK_PRODUCTS:
        return []
    
    current = MOCK_PRODUCTS[sku]
    current_category = current.get("category")
    
    # Find products in same category, excluding current
    similar = []
    for other_sku, product in MOCK_PRODUCTS.items():
        if other_sku != sku and product.get("category") == current_category:
            similar.append({
                "sku": product["sku"],
                "title": product["title"],
                "price": product["price"],
                "image_url": product["image_url"],
                "product_url": f"https://rje8b8-na.myshopify.com/products/{product['handle']}",
                "product_id": product["product_id"]
            })
    
    return similar[:3]  # Max 3 similar products


# ============================================================
# MOCK ORDERS (with enriched line items)
# ============================================================

def _create_mock_order(order_id, customer_id, email, status, items, total, days_ago=0, tracking=None):
    """Helper to create enriched mock orders"""
    base_date = "2026-07-15T10:20:00Z"
    return {
        "id": order_id,
        "order_number": order_id,
        "name": f"#{order_id}",
        "email": email,
        "phone": "555-1234",
        "created_at": base_date,
        "processed_at": base_date,
        "currency": "USD",
        "total": total,
        "subtotal_price": str(float(total) - 10.0),
        "total_tax": "10.00",
        "total_shipping": "0.00",
        "financial_status": "paid" if status not in ["cancelled", "refunded"] else "refunded",
        "fulfillment_status": "fulfilled" if status == "delivered" else ("partial" if status == "partially_shipped" else None),
        "status": status,
        "cancellable": status in ["processing", "partially_shipped"],
        "returnable": status in ["delivered", "partially_shipped"],
        "tracking": tracking,
        "customer": {
            "id": customer_id,
            "email": email,
            "first_name": "Merlin",
            "last_name": "K",
            "name": "Merlin K"
        },
        "shipping_address": {
            "address1": "123 Main St",
            "city": "San Francisco",
            "province": "California",
            "country": "United States",
            "zip": "94102"
        },
        "line_items": _enrich_line_items_with_products(items),
        "can_reorder": any(item.get("can_reorder") for item in items) if items else False
    }


MOCK_ORDERS = {
    "1001": _create_mock_order(
        "1001", "10446257848504", "techteam@uniqnex360.com", "delivered",
        [
            {"id": "2001", "sku": "WBH-001", "name": "Wireless Bluetooth Headphones", "title": "Wireless Bluetooth Headphones", "quantity": 1, "price": "79.99", "fulfillment_status": "fulfilled"},
            {"id": "2002", "sku": "USB-C-6FT", "name": "USB-C Charging Cable (6ft)", "title": "USB-C Charging Cable (6ft)", "quantity": 2, "price": "14.99", "fulfillment_status": "fulfilled"},
            {"id": "2003", "sku": "CASE-CLR", "name": "Phone Case - Clear", "title": "Phone Case - Clear", "quantity": 1, "price": "19.99", "fulfillment_status": "fulfilled"},
        ],
        "149.99",
        tracking={
            "carrier": "UPS",
            "tracking_number": "1Z999AA10123456784",
            "tracking_url": "https://www.ups.com/track?tracknum=1Z999AA10123456784"
        }
    ),
    "1002": _create_mock_order(
        "1002", "10446257848504", "techteam@uniqnex360.com", "partially_shipped",
        [
            {"id": "2004", "sku": "LAPTOP-STAND-ALU", "name": "Laptop Stand - Aluminum", "title": "Laptop Stand - Aluminum", "quantity": 1, "price": "89.99", "fulfillment_status": "fulfilled"},
            {"id": "2005", "sku": "KEYB-MECH-RGB", "name": "Mechanical Keyboard - RGB", "title": "Mechanical Keyboard - RGB", "quantity": 1, "price": "149.99", "fulfillment_status": None},
            {"id": "2006", "sku": "MOUSEPAD-LG", "name": "Mouse Pad - Large", "title": "Mouse Pad - Large", "quantity": 1, "price": "29.99", "fulfillment_status": None},
            {"id": "2007", "sku": "USBHUB-7", "name": "USB Hub - 7 Port", "title": "USB Hub - 7 Port", "quantity": 1, "price": "19.99", "fulfillment_status": "fulfilled"},
        ],
        "299.99",
        tracking={
            "carrier": "FedEx",
            "tracking_number": "123456789012",
            "tracking_url": "https://www.fedex.com/fedextrack/?trknbr=123456789012"
        }
    ),
    "1003": _create_mock_order(
        "1003", "10446257848504", "techteam@uniqnex360.com", "processing",
        [
            {"id": "2008", "sku": "CHRG-FAST", "name": "Phone Charger - Fast Charge", "title": "Phone Charger - Fast Charge", "quantity": 1, "price": "29.99", "fulfillment_status": None},
            {"id": "2009", "sku": "SCRN-PROT-TG", "name": "Screen Protector - Tempered Glass", "title": "Screen Protector - Tempered Glass", "quantity": 2, "price": "9.99", "fulfillment_status": None},
        ],
        "49.99"
    ),
    "1004": _create_mock_order(
        "1004", "10446257848504", "techteam@uniqnex360.com", "cancelled",
        [
            {"id": "2010", "sku": "DESK-LAMP-LED", "name": "Desk Lamp - LED", "title": "Desk Lamp - LED", "quantity": 1, "price": "89.99", "fulfillment_status": None},
        ],
        "89.99"
    )
}


# ============================================================
# ENDPOINTS
# ============================================================

@router.get("/mock/orders/list")
async def mock_list_orders(
    customer_id: Optional[str] = None,
    email: Optional[str] = None,
    x_api_key: str = Header(..., alias="X-API-Key")
):
    if x_api_key != "demo_key_12345":
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    orders = []
    for order_id, order in MOCK_ORDERS.items():
        if customer_id and order["customer"]["id"] == customer_id:
            orders.append(order)
        elif email and order["email"].lower() == email.lower():
            orders.append(order)
    
    orders.sort(key=lambda x: x["created_at"], reverse=True)
    
    return {
        "orders": orders,
        "total": len(orders),
        "customer_id": customer_id,
        "email": email
    }


@router.get("/mock/orders/status")
async def mock_get_order(
    order_id: str,
    x_api_key: str = Header(..., alias="X-API-Key")
):
    if x_api_key != "demo_key_12345":
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    order = MOCK_ORDERS.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return order


@router.post("/mock/orders/verify")
async def mock_verify_order(
    order_number: str,
    email: Optional[str] = None,
    phone_last4: Optional[str] = None,
    x_api_key: str = Header(..., alias="X-API-Key")
):
    if x_api_key != "demo_key_12345":
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    order = MOCK_ORDERS.get(order_number)
    if not order:
        return {"verified": False, "message": "Order not found"}
    
    if email and order["email"].lower() == email.lower():
        import jwt
        secret = os.getenv("VERIFY_TOKEN_SECRET", "change-this-in-production")
        token = jwt.encode(
            {"order_id": order["id"], "exp": int(time.time()) + 300},
            secret, algorithm="HS256"
        )
        return {"verified": True, "order_id": order["id"], "verify_token": token}
    
    if phone_last4 and order["phone"][-4:] == phone_last4:
        import jwt
        secret = os.getenv("VERIFY_TOKEN_SECRET", "change-this-in-production")
        token = jwt.encode(
            {"order_id": order["id"], "exp": int(time.time()) + 300},
            secret, algorithm="HS256"
        )
        return {"verified": True, "order_id": order["id"], "verify_token": token}
    
    return {"verified": False, "message": "Order details don't match"}


@router.post("/mock/orders/cancel")
async def mock_cancel_order(
    order_id: str,
    reason: str = "customer",
    x_api_key: str = Header(..., alias="X-API-Key")
):
    if x_api_key != "demo_key_12345":
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    order = MOCK_ORDERS.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if not order["cancellable"]:
        raise HTTPException(
            status_code=409,
            detail=f"Order #{order['order_number']} cannot be cancelled (status: {order['status']})"
        )
    
    order["status"] = "cancelled"
    order["financial_status"] = "refunded"
    order["cancellable"] = False
    order["fulfillment_status"] = None
    
    return {
        "success": True,
        "action": "cancelled",
        "order_id": order["id"],
        "order_number": order["order_number"],
        "new_status": "cancelled",
        "message": f"Order #{order['order_number']} has been cancelled. Refund of ${order['total']} will be processed in 5-10 business days.",
        "refund_eta": "5-10 business days"
    }


@router.post("/mock/orders/return")
async def mock_create_return(
    order_id: str,
    item_skus: List[str],
    reason: str = "Customer initiated return",
    x_api_key: str = Header(..., alias="X-API-Key")
):
    if x_api_key != "demo_key_12345":
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    order = MOCK_ORDERS.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if not order["returnable"]:
        raise HTTPException(
            status_code=409,
            detail=f"Order #{order['order_number']} is not eligible for return"
        )
    
    matching_items = [
        item for item in order["line_items"]
        if item.get("sku") in item_skus
    ]
    
    if not matching_items:
        raise HTTPException(
            status_code=400,
            detail="No matching items found in this order"
        )
    
    return {
        "success": True,
        "action": "return_initiated",
        "order_id": order["id"],
        "order_number": order["order_number"],
        "new_status": "return_initiated",
        "reference": f"RET-{random.randint(100000, 999999)}",
        "message": f"Return initiated for order #{order['order_number']}. {len(matching_items)} item(s) will be refunded.",
        "refund_eta": "5-10 business days",
        "items_returned": [
            {"sku": item["sku"], "name": item["name"], "product_url": item.get("product_url")}
            for item in matching_items
        ]
    }


@router.get("/mock/products/search")
async def mock_product_search(
    q: str = "",
    sku: Optional[str] = None,
    x_api_key: str = Header(..., alias="X-API-Key")
):
    """Search mock products for re-ordering"""
    if x_api_key != "demo_key_12345":
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    if sku:
        product = MOCK_PRODUCTS.get(sku)
        return {"product": product, "found": product is not None}
    
    results = []
    q_lower = q.lower()
    for product_sku, product in MOCK_PRODUCTS.items():
        if (q_lower in product["title"].lower() or 
            q_lower in product.get("category", "").lower() or
            any(q_lower in tag.lower() for tag in product.get("tags", []))):
            results.append({
                **product,
                "product_url": f"https://rje8b8-na.myshopify.com/products/{product['handle']}"
            })
    
    return {"products": results, "total": len(results)}


@router.post("/mock/orders/reorder")
async def mock_reorder(
    order_id: str,
    item_skus: List[str],
    x_api_key: str = Header(..., alias="X-API-Key")
):
    """Create a re-order from a previous order"""
    if x_api_key != "demo_key_12345":
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    order = MOCK_ORDERS.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    items_to_reorder = [
        item for item in order["line_items"]
        if item.get("sku") in item_skus and item.get("can_reorder")
    ]
    
    if not items_to_reorder:
        raise HTTPException(
            status_code=400,
            detail="No items available for re-order (out of stock or not reorderable)"
        )
    
    # Generate cart URL
    cart_items = "&".join([
        f"{item['product_id']}:{item['quantity']}" 
        for item in items_to_reorder
    ])
    cart_url = f"https://rje8b8-na.myshopify.com/cart/add?items[{cart_items}]"
    
    return {
        "success": True,
        "action": "cart_created",
        "cart_url": cart_url,
        "items": [
            {
                "sku": item["sku"],
                "name": item["name"],
                "quantity": item["quantity"],
                "price": item["price"],
                "product_url": item.get("product_url"),
                "image_url": item.get("image_url")
            }
            for item in items_to_reorder
        ],
        "total_items": len(items_to_reorder),
        "message": f"Added {len(items_to_reorder)} item(s) to your cart!"
    }