from openai import OpenAI
from openai import OpenAIError
from fastapi import HTTPException
import os
import re
from dotenv import load_dotenv
load_dotenv()
OPEN_AI_KEY = os.getenv("OPEN_AI_KEY")
GOOGLE_GEMINI_KEY = os.getenv("GOOGLE_GEMINI_API_KEY")
client = OpenAI(api_key=OPEN_AI_KEY)


def ask_gemini(prompt):
    import requests
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-lite-latest:generateContent?key={GOOGLE_GEMINI_KEY}"
    headers = {'Content-Type': 'application/json'}
    payload = {
        'contents': [{
            'parts': [{'text': prompt}]
        }]
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        if 'candidates' in result and len(result['candidates']) > 0:
            return result['candidates'][0]['content']['parts'][0]['text']
        return "Sorry, I couldn't generate a response."
    except Exception as e:
        return f"Error: {str(e)}"


# class ChatbotService:
#     def __init__(self):
#         pass

#     async def process_chat_message(
#         self,
#         user_query: str,
#         product_context: dict,
#         session_id: str = None,
#         x_api_key: str = None,
#     ):
#         """
#         Main chat handler. Detects intent and routes to:
#           - Order management (status/cancel/return)
#           - Product Q&A (existing flow)
#         """
#         if not session_id:
#             session_id = "default-session"
#         intent = self._classify_intent(user_query, product_context)
#         if intent in ("order_status", "order_cancel", "order_return") and x_api_key:
#             return await self._handle_order_intent(
#                 intent, user_query, session_id, product_context, x_api_key
#             )
#         return await self._handle_product_question(user_query, product_context)

#     def _classify_intent(self, user_query: str, product_context: dict) -> str:
#         """
#         Classify user intent.
#         Returns: 'order_status' | 'order_cancel' | 'order_return' | 'product'
#         """
#         import re
#         msg = user_query.lower().strip()

#         # Cancel keywords
#         cancel_keywords = [
#             "cancel my order", "cancel order", "cancel this",
#             "i want to cancel", "i need to cancel", "stop my order",
#             "don't want this anymore", "changed my mind"
#         ]
#         if any(kw in msg for kw in cancel_keywords):
#             return "order_cancel"

#         # Return keywords
#         return_keywords = [
#             "return my order", "return this", "i want to return",
#             "i need to return", "refund", "get my money back",
#             "send it back", "exchange"
#         ]
#         if any(kw in msg for kw in return_keywords):
#             return "order_return"

#         # Status keywords
#         status_keywords = [
#             "my order", "order status", "where is my order",
#             "where's my order", "track my order", "track my package",
#             "check my order", "order update", "when will",
#             "shipping status", "delivery status", "has it shipped",
#             "did it ship", "arrived yet", "where is my package",
#             "show my orders", "list my orders", "my purchases",
#             "show orders", "view orders"
#         ]
#         if any(kw in msg for kw in status_keywords):
#             return "order_status"

#         # ✅ NEW: Detect standalone order numbers (3-10 digits)
#         order_number_pattern = r'^\s*(?:#|order\s*(?:number\s*)?(?:\s*is\s*)?)?(\d{3,10})\s*$'
#         if re.match(order_number_pattern, msg):
#             return "order_status"

#         # ✅ NEW: Detect customer ID (10+ digits - Shopify customer IDs)
#         customer_id_pattern = r'^\s*\d{10,15}\s*$'
#         if re.match(customer_id_pattern, msg):
#             return "order_status"

#         # ✅ NEW: Detect order number with context
#         if re.search(r'order\s*#?\s*\d{3,10}', msg, re.IGNORECASE):
#             return "order_status"

#         return "product"

#     async def _handle_order_intent(
#         self,
#         intent: str,
#         user_query: str,
#         session_id: str,
#         product_context: dict,
#         x_api_key: str,
#     ) -> str:
#         """Route order intents to the orchestration layer"""
#         from services.order_intent_handler import (
#             handle_order_status_query,
#             handle_order_cancel,
#             handle_order_return,
#         )
#         context_with_customer = dict(product_context)
#         if not context_with_customer.get("customer_id"):
#             context_with_customer["customer_id"] = None
#         try:
#             if intent == "order_status":
#                 result = await handle_order_status_query(
#                     user_query, session_id, context_with_customer, x_api_key
#                 )
#             elif intent == "order_cancel":
#                 result = await handle_order_cancel(
#                     user_query, session_id, context_with_customer, x_api_key
#                 )
#             elif intent == "order_return":
#                 result = await handle_order_return(
#                     user_query, session_id, context_with_customer, x_api_key
#                 )
#             else:
#                 return "I'm not sure how to help with that."
#             reply = result.get(
#                 "reply_text", "I couldn't process that request.")
#             if result.get("escalate"):
#                 reply += "\n\n[ESCALATE TO HUMAN AGENT]"
#             return reply
#         except Exception as e:
#             print(f"Order intent handler error: {e}")
#             import traceback
#             traceback.print_exc()
#             return "I'm having trouble looking up your order right now. Please try again in a moment."

#     async def _handle_product_question(
#         self,
#         user_query: str,
#         product_context: dict,
#     ) -> str:
#         """Existing product Q&A flow with OpenAI/Gemini fallback"""
#         try:
#             product_name = product_context.get('name', 'this product')
#             product_sku = product_context.get('sku', 'N/A')
#             product_description = product_context.get('description', 'N/A')
#             product_price = product_context.get('price', 'N/A')
#             product_brand = product_context.get('brand', 'N/A')
#             product_category = product_context.get('category', 'N/A')
#             in_stock = product_context.get('inStock', True)
#             product_info = f"""
# Product Name: {product_name}
# SKU: {product_sku}
# Brand: {product_brand}
# Category: {product_category}
# Price: ${product_price}
# Description: {product_description}
# Availability: {'In Stock' if in_stock else 'Out of Stock'}
#             """.strip()
#             prompt = f"""
# You are an AI assistant for an e-commerce website. Your task is to provide clear and relevant answers based on the given product details.
# 1. Answer concisely based only on the product details provided.
# 2. If the user asks about orders, cancellations, returns, or tracking, respond that you can help with that and ask for their order number.
# 3. Avoid raw data dumps—only provide direct human-readable responses.
# ---
# {product_info}
# ---
# {user_query}
#             """
#             try:
#                 response = client.chat.completions.create(
#                     model="gpt-3.5-turbo",
#                     messages=[
#                         {"role": "system",
#                             "content": "You are a helpful product assistant."},
#                         {"role": "user", "content": prompt}
#                     ],
#                     temperature=0.7,
#                     max_tokens=300
#                 )
#                 return response.choices[0].message.content.strip()
#             except OpenAIError as e:
#                 print(f"OpenAI failed, falling back to Gemini: {str(e)}")
#                 return ask_gemini(prompt)
#         except Exception as e:
#             print(f"Error in _handle_product_question: {e}")
#             import traceback
#             traceback.print_exc()
#             raise HTTPException(
#                 status_code=500, detail=f"Error processing message: {str(e)}")
class ChatbotService:
    def __init__(self):
        pass
    
    async def process_chat_message(
        self,
        user_query: str,
        product_context: dict,
        session_id: str = None,
        x_api_key: str = None,
    ):
        if not session_id:
            session_id = "default-session"
        
        # Detect intent
        intent = self._classify_intent(user_query, product_context)
        
        if intent in ("order_status", "order_cancel", "order_return") and x_api_key:
            return await self._handle_order_intent(
                intent, user_query, session_id, product_context, x_api_key
            )
        
        return await self._handle_product_question(user_query, product_context)
    
    def _classify_intent(self, user_query: str, product_context: dict) -> str:
        import re
        msg = user_query.lower().strip()
        
        # Cancel keywords
        cancel_keywords = [
            "cancel my order", "cancel order", "cancel this",
            "i want to cancel", "i need to cancel", "stop my order",
            "don't want this anymore", "changed my mind"
        ]
        if any(kw in msg for kw in cancel_keywords):
            return "order_cancel"
        
        # Return keywords
        return_keywords = [
            "return my order", "return this", "i want to return",
            "i need to return", "refund", "get my money back",
            "send it back", "exchange"
        ]
        if any(kw in msg for kw in return_keywords):
            return "order_return"
        
        # Status keywords
        status_keywords = [
            "my order", "order status", "where is my order",
            "where's my order", "track my order", "track my package",
            "check my order", "order update", "when will",
            "shipping status", "delivery status", "has it shipped",
            "did it ship", "arrived yet", "where is my package",
            "show my orders", "list my orders", "my purchases",
            "show orders", "view orders"
        ]
        if any(kw in msg for kw in status_keywords):
            return "order_status"
        
        # Standalone order numbers (3-10 digits)
        order_number_pattern = r'^\s*(?:#|order\s*(?:number\s*)?(?:\s*is\s*)?)?(\d{3,10})\s*$'
        if re.match(order_number_pattern, msg):
            return "order_status"
        
        # Customer IDs (10+ digits)
        customer_id_pattern = r'^\s*\d{10,15}\s*$'
        if re.match(customer_id_pattern, msg):
            return "order_status"
        
        # Order with context
        if re.search(r'order\s*#?\s*\d{3,10}', msg, re.IGNORECASE):
            return "order_status"
        
        return "product"
    
    async def _handle_order_intent(
        self,
        intent: str,
        user_query: str,
        session_id: str,
        product_context: dict,
        x_api_key: str,
    ) -> str:
        """
        Handle order intents:
        1. Fetch order data from API (no AI)
        2. Pass data to LLM to format response
        3. LLM orchestrates the conversation
        """
        try:
            # Get session state
            sess = self._get_order_session(session_id)
            
            # Step 1: Fetch order data (NO AI)
            order_data = await self._fetch_order_data(
                intent, user_query, sess, product_context, x_api_key
            )
            
            if not order_data:
                return "I couldn't find any orders. Please check the order number or try again."
            
            # Step 2: Use LLM to format the response
            llm_response = await self._llm_orchestrate_order(
                intent, user_query, order_data, sess
            )
            
            return llm_response
            
        except Exception as e:
            print(f"Order intent error: {e}")
            import traceback
            traceback.print_exc()
            return "I'm having trouble looking up your order. Please try again."
    
    async def _fetch_order_data(
        self,
        intent: str,
        user_query: str,
        sess: dict,
        product_context: dict,
        x_api_key: str,
    ) -> dict:
        """
        Fetch order data from API - NO AI, just data retrieval
        """
        import re
        import httpx
        
        # Extract order number or customer ID
        customer_id_from_msg = None
        if user_query.strip().isdigit() and len(user_query.strip()) >= 10:
            customer_id_from_msg = user_query.strip()
        
        order_match = re.search(r'(\d{3,10})', user_query)
        order_number = order_match.group(1) if order_match and not customer_id_from_msg else None
        
        # Get customer ID
        customer_id = (
            customer_id_from_msg or 
            sess.get("customer_id") or 
            product_context.get("customer_id")
        )
        
        # Fetch order(s) from mock API
        async with httpx.AsyncClient(timeout=10) as client:
            if order_number:
                # Fetch specific order
                response = await client.get(
                    f"https://convesational-commerce-backend.onrender.com/api/v1/mock/orders/status",
                    params={"order_id": order_number},
                    headers={"X-API-Key": "demo_key_12345"}
                )
                if response.status_code == 200:
                    order = response.json()
                    sess["current_order"] = order
                    sess["current_order_id"] = order["id"]
                    return {"type": "single_order", "order": order}
            
            elif customer_id:
                # Fetch customer's orders
                response = await client.get(
                    f"https://convesational-commerce-backend.onrender.com/api/v1/mock/orders/list",
                    params={"customer_id": customer_id},
                    headers={"X-API-Key": "demo_key_12345"}
                )
                if response.status_code == 200:
                    data = response.json()
                    orders = data.get("orders", [])
                    sess["customer_id"] = customer_id
                    sess["all_orders"] = orders
                    return {"type": "order_list", "orders": orders, "customer_id": customer_id}
        
        return None
    
    async def _llm_orchestrate_order(
        self,
        intent: str,
        user_query: str,
        order_data: dict,
        sess: dict
    ) -> str:
        """
        Use LLM to format order data into a friendly response
        The LLM understands the data and responds naturally
        """
        import json
        
        # Prepare context for LLM
        if order_data["type"] == "single_order":
            order = order_data["order"]
            data_context = f"""
You have access to the following order data:
{json.dumps(order, indent=2)}

User's request: {user_query}
Intent: {intent}
"""
        else:  # order_list
            orders = order_data["orders"]
            data_context = f"""
You have access to {len(orders)} orders for this customer:
{json.dumps(orders, indent=2)}

User's request: {user_query}
Intent: {intent}
"""
        
        # Build prompt for LLM
        prompt = f"""You are a helpful customer service assistant for an e-commerce store.

{data_context}

Instructions:
1. Answer the user's question using ONLY the order data provided
2. Be friendly, concise, and natural
3. If the user wants to cancel an order, check if it's cancellable first and ask for confirmation
4. If the user wants to return an order, check if it's returnable and ask which items
5. Include relevant details like tracking links, product links, and order status
6. Format the response clearly with line breaks
7. Don't make up information not in the data
8. If asking for confirmation, make it clear what action will be taken
"""
        
        try:
            # Call LLM
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful customer service assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            return response.choices[0].message.content.strip()
        except OpenAIError as e:
            print(f"OpenAI failed: {e}, falling back to Gemini")
            return ask_gemini(prompt)
    
    def _get_order_session(self, session_id: str) -> dict:
        """Get or create order session state"""
        if not hasattr(self, '_order_sessions'):
            self._order_sessions = {}
        
        if session_id not in self._order_sessions:
            self._order_sessions[session_id] = {
                "customer_id": None,
                "current_order": None,
                "current_order_id": None,
                "all_orders": []
            }
        return self._order_sessions[session_id]
    
    async def _handle_product_question(
        self,
        user_query: str,
        product_context: dict,
    ) -> str:
        """Handle general product questions with AI"""
        try:
            product_name = product_context.get('name', 'this product')
            product_sku = product_context.get('sku', 'N/A')
            product_description = product_context.get('description', 'N/A')
            product_price = product_context.get('price', 'N/A')
            product_brand = product_context.get('brand', 'N/A')
            product_category = product_context.get('category', 'N/A')
            in_stock = product_context.get('inStock', True)
            
            product_info = f"""
Product Name: {product_name}
SKU: {product_sku}
Brand: {product_brand}
Category: {product_category}
Price: ${product_price}
Description: {product_description}
Availability: {'In Stock' if in_stock else 'Out of Stock'}
            """.strip()
            
            prompt = f"""
You are a helpful product assistant. Answer questions about this product only.
Keep responses concise and based only on the product details provided.
---
{product_info}
---
{user_query}
            """
            
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a helpful product assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=300
                )
                return response.choices[0].message.content.strip()
            except OpenAIError as e:
                print(f"OpenAI failed, falling back to Gemini: {str(e)}")
                return ask_gemini(prompt)
        except Exception as e:
            print(f"Error in _handle_product_question: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=500, detail=f"Error processing message: {str(e)}")