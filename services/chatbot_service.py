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
#2
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
#         if not session_id:
#             session_id = "default-session"
        
#         # Detect intent
#         intent = self._classify_intent(user_query, product_context)
        
#         if intent in ("order_status", "order_cancel", "order_return") and x_api_key:
#             return await self._handle_order_intent(
#                 intent, user_query, session_id, product_context, x_api_key
#             )
        
#         return await self._handle_product_question(user_query, product_context)
    
#     def _classify_intent(self, user_query: str, product_context: dict) -> str:
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
        
#         # Standalone order numbers (3-10 digits)
#         order_number_pattern = r'^\s*(?:#|order\s*(?:number\s*)?(?:\s*is\s*)?)?(\d{3,10})\s*$'
#         if re.match(order_number_pattern, msg):
#             return "order_status"
        
#         # Customer IDs (10+ digits)
#         customer_id_pattern = r'^\s*\d{10,15}\s*$'
#         if re.match(customer_id_pattern, msg):
#             return "order_status"
        
#         # Order with context
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
#         try:
#             sess = self._get_order_session(session_id)
            
#             # Check for confirmation of pending action
#             if sess.get("pending_action") and self._is_confirmation(user_query):
#                 response_text = await self._execute_pending_action(sess, user_query)
#                 self._add_to_history(sess, user_query, response_text)
#                 return response_text
            
#             # Check for decline
#             if sess.get("pending_action") and self._is_decline(user_query):
#                 sess["pending_action"] = None
#                 response_text = "No problem, I won't proceed with that. Anything else?"
#                 self._add_to_history(sess, user_query, response_text)
#                 return response_text
            
#             # Fetch order data
#             order_data = await self._fetch_order_data(
#                 intent, user_query, sess, product_context, x_api_key
#             )
            
#             if not order_data:
#                 response_text = "I couldn't find any orders. Please check the order number or try again."
#                 self._add_to_history(sess, user_query, response_text)
#                 return response_text
            
#             # Use LLM with full context
#             response_text = await self._llm_orchestrate_order(
#                 intent, user_query, order_data, sess
#             )
            
#             # Track conversation
#             self._add_to_history(sess, user_query, response_text)
            
#             # Set pending action if LLM is asking for confirmation
#             if self._is_asking_confirmation(response_text):
#                 if order_data["type"] == "single_order":
#                     order = order_data["order"]
#                     if intent == "order_cancel" and order.get("cancellable"):
#                         sess["pending_action"] = {
#                             "action": "cancel",
#                             "order_id": order["id"]
#                         }
#                     elif intent == "order_return" and order.get("returnable"):
#                         sess["pending_action"] = {
#                             "action": "return",
#                             "order_id": order["id"],
#                             "items": [item["sku"] for item in order.get("line_items", []) if item.get("sku")]
#                         }
            
#             return response_text
            
#         except Exception as e:
#             print(f"Order intent error: {e}")
#             import traceback
#             traceback.print_exc()
#             return "I'm having trouble. Please try again."


#     def _add_to_history(self, sess: dict, user_msg: str, assistant_msg: str):
#         """Add exchange to conversation history"""
#         if "conversation_history" not in sess:
#             sess["conversation_history"] = []
        
#         sess["conversation_history"].append({
#             "user": user_msg,
#             "assistant": assistant_msg
#         })
        
#         # Keep only last 5 exchanges
#         if len(sess["conversation_history"]) > 5:
#             sess["conversation_history"] = sess["conversation_history"][-5:]


#     def _is_asking_confirmation(self, response: str) -> bool:
#         """Check if LLM is asking for confirmation"""
#         response_lower = response.lower()
#         confirm_phrases = [
#             "shall i proceed",
#             "yes/no",
#             "confirm",
#             "shall i cancel",
#             "shall i process"
#         ]
#         return any(phrase in response_lower for phrase in confirm_phrases)


#     def _is_confirmation(self, message: str) -> bool:
#         """Check if message is a confirmation"""
#         msg = message.lower().strip()
#         confirmations = ['yes', 'y', 'yeah', 'yep', 'confirm', 'ok', 'okay', 'sure', 'proceed', 'do it', 'go ahead']
#         return msg in confirmations


#     def _is_decline(self, message: str) -> bool:
#         """Check if message is a decline"""
#         msg = message.lower().strip()
#         declines = ['no', 'n', 'nope', 'cancel', 'nevermind', 'never mind', "don't", 'stop', 'abort']
#         return msg in declines
        
#     async def _fetch_order_data(
#         self,
#         intent: str,
#         user_query: str,
#         sess: dict,
#         product_context: dict,
#         x_api_key: str,
#     ) -> dict:
#         """
#         Fetch order data from API - NO AI, just data retrieval
#         """
#         import re
#         import httpx
        
#         # Extract order number or customer ID
#         customer_id_from_msg = None
#         if user_query.strip().isdigit() and len(user_query.strip()) >= 10:
#             customer_id_from_msg = user_query.strip()
        
#         order_match = re.search(r'(\d{3,10})', user_query)
#         order_number = order_match.group(1) if order_match and not customer_id_from_msg else None
        
#         # Get customer ID
#         customer_id = (
#             customer_id_from_msg or 
#             sess.get("customer_id") or 
#             product_context.get("customer_id")
#         )
        
#         # Fetch order(s) from mock API
#         async with httpx.AsyncClient(timeout=10) as client:
#             if order_number:
#                 # Fetch specific order
#                 response = await client.get(
#                     f"https://convesational-commerce-backend.onrender.com/api/v1/mock/orders/status",
#                     params={"order_id": order_number},
#                     headers={"X-API-Key": "demo_key_12345"}
#                 )
#                 if response.status_code == 200:
#                     order = response.json()
#                     sess["current_order"] = order
#                     sess["current_order_id"] = order["id"]
#                     return {"type": "single_order", "order": order}
            
#             elif customer_id:
#                 # Fetch customer's orders
#                 response = await client.get(
#                     f"https://convesational-commerce-backend.onrender.com/api/v1/mock/orders/list",
#                     params={"customer_id": customer_id},
#                     headers={"X-API-Key": "demo_key_12345"}
#                 )
#                 if response.status_code == 200:
#                     data = response.json()
#                     orders = data.get("orders", [])
#                     sess["customer_id"] = customer_id
#                     sess["all_orders"] = orders
#                     return {"type": "order_list", "orders": orders, "customer_id": customer_id}
        
#         return None

#     async def _llm_orchestrate_order(
#         self,
#         intent: str,
#         user_query: str,
#         order_data: dict,
#         sess: dict
#     ) -> str:
#         """
#         Use LLM with full session context so it knows what "it" refers to
#         """
#         import json
        
#         # Build session context
#         session_context = ""
        
#         # Add last discussed order(s)
#         if sess.get("last_discussed_order"):
#             last_order = sess["last_discussed_order"]
#             session_context = f"""
#     CONVERSATION CONTEXT:
#     The user previously asked about their orders and you showed them a list.
#     When they say "it", "this order", "the order", "cancel it", "return it", they are referring to the LAST order they mentioned or were viewing.

#     LAST DISCUSSED ORDER:
#     {json.dumps(last_order, indent=2)}
#     """
        
#         # Add pending actions
#         if sess.get("pending_action"):
#             action = sess["pending_action"]
#             session_context += f"""
#     PENDING ACTION: User has a pending '{action.get('action')}' action on Order #{action.get('order_id')}.
#     If they say "yes" or "confirm", execute the action.
#     If they say "no" or "cancel", clear the pending action.
#     """
        
#         # Add recent conversation history
#         if sess.get("conversation_history"):
#             history = sess["conversation_history"][-3:]  # Last 3 exchanges
#             session_context += "\nRECENT CONVERSATION:\n"
#             for exchange in history:
#                 session_context += f"User: {exchange['user']}\nAssistant: {exchange['assistant'][:100]}...\n\n"
        
#         # Prepare data based on what's being asked
#         if order_data["type"] == "single_order":
#             order = order_data["order"]
#             # Update last discussed
#             sess["last_discussed_order"] = order
            
#             data_context = f"""
#     CURRENT ORDER DATA:
#     {json.dumps(order, indent=2)}

#     {session_context}

#     USER'S NEW REQUEST: {user_query}
#     INTENT: {intent}
#     """
#         else:
#             # Order list
#             orders = order_data["orders"]
#             data_context = f"""
#     AVAILABLE ORDERS ({len(orders)} total):
#     {json.dumps(orders, indent=2)}

#     {session_context}

#     USER'S NEW REQUEST: {user_query}
#     INTENT: {intent}
#     """
        
#         # Enhanced prompt with strong context emphasis
#         prompt = f"""You are a helpful customer service assistant for an e-commerce store with access to order data.

#     {data_context}

#     CRITICAL INSTRUCTIONS - READ CAREFULLY:

#     1. **CONTEXT AWARENESS**: If the user says "it", "this order", "the order", "cancel it", "return it" - they are referring to the LAST DISCUSSED ORDER (shown above). Use that order.

#     2. **AMBIGUITY RESOLUTION**: 
#     - If user says "cancel it" and there's a last discussed order → cancel THAT order
#     - If user says "cancel it" and there's NO last discussed order → ask "Which order would you like to cancel?"
#     - If multiple orders and user says "the first one" or "the delivered one" → use the specific one they reference

#     3. **CANCELLATIONS**:
#     - Check if the order is cancellable (look for "cancellable": true)
#     - If YES: Ask "Shall I cancel Order #XXX for $XXX? (yes/no)"
#     - If NO: Explain why (e.g., "already delivered", "already shipped") and offer return instead

#     4. **RETURNS**:
#     - Check if returnable (look for "returnable": true)
#     - If YES: List the items and ask "Which items would you like to return?"

#     5. **STATUS QUERIES**: Provide order number, status, tracking info, items

#     6. **FORMATTING**: Use clear line breaks, include tracking links and product links

#     7. **BE CONCISE**: Don't dump all data, answer the specific question

#     8. **NO HALLUCINATIONS**: Only use data provided, don't make up information
#     """
        
#         try:
#             response = client.chat.completions.create(
#                 model="gpt-3.5-turbo",
#                 messages=[
#                     {"role": "system", "content": "You are a helpful customer service assistant. You MUST use conversation context to understand ambiguous references like 'it' or 'this order'."},
#                     {"role": "user", "content": prompt}
#                 ],
#                 temperature=0.7,
#                 max_tokens=500
#             )
#             return response.choices[0].message.content.strip()
#         except OpenAIError as e:
#             print(f"OpenAI failed: {e}, falling back to Gemini")
#             return ask_gemini(prompt)

#     def _get_order_session(self, session_id: str) -> dict:
#         """Get or create order session state"""
#         if not hasattr(self, '_order_sessions'):
#             self._order_sessions = {}
        
#         if session_id not in self._order_sessions:
#             self._order_sessions[session_id] = {
#                 "customer_id": None,
#                 "last_discussed_order": None,
#                 "all_orders": [],
#                 "pending_action": None,
#                 "conversation_history": []
#             }
#         return self._order_sessions[session_id]

#     async def _handle_product_question(
#         self,
#         user_query: str,
#         product_context: dict,
#     ) -> str:
#         """Handle general product questions with AI"""
#         try:
#             product_name = product_context.get('name', 'this product')
#             product_sku = product_context.get('sku', 'N/A')
#             product_description = product_context.get('description', 'N/A')
#             product_price = product_context.get('price', 'N/A')
#             product_brand = product_context.get('brand', 'N/A')
#             product_category = product_context.get('category', 'N/A')
#             in_stock = product_context.get('inStock', True)
            
#             product_info = f"""
#     Product Name: {product_name}
#     SKU: {product_sku}
#     Brand: {product_brand}
#     Category: {product_category}
#     Price: ${product_price}
#     Description: {product_description}
#     Availability: {'In Stock' if in_stock else 'Out of Stock'}
#             """.strip()
            
#             prompt = f"""
#     You are a helpful product assistant. Answer questions about this product only.
#     Keep responses concise and based only on the product details provided.
#     ---
#     {product_info}
#     ---
#     {user_query}
#             """
            
#             try:
#                 response = client.chat.completions.create(
#                     model="gpt-3.5-turbo",
#                     messages=[
#                         {"role": "system", "content": "You are a helpful product assistant."},
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
import os
import re
import json
import httpx
import logging
import requests
from openai import OpenAI, OpenAIError
from fastapi import HTTPException
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Initialize Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Constants
OPEN_AI_KEY = os.getenv("OPEN_AI_KEY")
GOOGLE_GEMINI_KEY = os.getenv("GOOGLE_GEMINI_API_KEY")
BACKEND_BASE_URL = "https://convesational-commerce-backend.onrender.com/api/v1"
API_KEY_HEADER = {"X-API-Key": "demo_key_12345"}

# Initialize OpenAI
client = OpenAI(api_key=OPEN_AI_KEY)

def ask_gemini(prompt: str) -> str:
    """Fallback AI service using Google Gemini 1.5 Flash"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_GEMINI_KEY}"
    headers = {'Content-Type': 'application/json'}
    payload = {'contents': [{'parts': [{'text': prompt}]}]}
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        result = response.json()
        if 'candidates' in result and len(result['candidates']) > 0:
            return result['candidates'][0]['content']['parts'][0]['text']
        return "I'm sorry, I'm having trouble processing that right now."
    except Exception as e:
        logger.error(f"Gemini API Error: {str(e)}")
        return "I'm experiencing connection issues. Please try again in a moment."

class ChatbotService:
    # Class-level session store to persist across requests in the process
    _order_sessions: Dict[str, Dict[str, Any]] = {}
    
    # Shared async client for production performance
    _http_client = httpx.AsyncClient(timeout=10.0)

    def __init__(self):
        pass

    # ============================================================
    # MAIN ENTRY POINT
    # ============================================================
    async def process_chat_message(
        self,
        user_query: str,
        product_context: dict,
        session_id: str = None,
        x_api_key: str = None,
    ) -> str:
        if not session_id:
            session_id = "default-session"
        
        sess = self._get_order_session(session_id)
        
        # 1. Handle Active Confirmations (Yes/No)
        # We check this FIRST so context isn't lost to the intent classifier
        if sess.get("pending_action"):
            if self._is_confirmation(user_query):
                response_text = await self._execute_pending_action(sess, user_query)
                self._add_to_history(sess, user_query, response_text)
                return response_text
            
            if self._is_decline(user_query):
                sess["pending_action"] = None
                response_text = "No problem, I've cancelled that request. Is there anything else I can help with?"
                self._add_to_history(sess, user_query, response_text)
                return response_text

        # 2. Intent Detection
        intent = self._classify_intent(user_query, product_context)
        
        # 3. Routing
        if intent in ("order_status", "order_cancel", "order_return") and x_api_key:
            return await self._handle_order_intent(
                intent, user_query, session_id, product_context, x_api_key
            )
        
        # 4. Fallback to Product Q&A
        return await self._handle_product_question(user_query, product_context)

    # ============================================================
    # INTENT CLASSIFICATION (Maintained exactly as requested)
    # ============================================================
    def _classify_intent(self, user_query: str, product_context: dict) -> str:
        msg = user_query.lower().strip()
        
        # Cancellation (including common typos)
        cancel_keywords = ["cancel", "canel", "stop my order", "dont want", "changed my mind"]
        if any(kw in msg for kw in cancel_keywords):
            return "order_cancel"
        
        # Returns
        return_keywords = ["return", "refund", "get my money back", "exchange"]
        if any(kw in msg for kw in return_keywords):
            return "order_return"
        
        # Status/Tracking
        status_keywords = ["order", "status", "where is", "track", "shipped", "arrived", "my package", "show my orders", "list my orders"]
        if any(kw in msg for kw in status_keywords):
            return "order_status"
        
        # Identifiers
        if re.match(r'^\s*(?:#|order\s*)?(\d{3,15})\s*$', msg):
            return "order_status"
        
        if re.search(r'order\s*#?\s*\d{3,10}', msg, re.IGNORECASE):
            return "order_status"
        
        return "product"

    # ============================================================
    # ORDER HANDLING LOGIC
    # ============================================================
    async def _handle_order_intent(self, intent, user_query, session_id, product_context, x_api_key) -> str:
        try:
            sess = self._get_order_session(session_id)
            order_data = await self._fetch_order_data(intent, user_query, sess, product_context, x_api_key)
            
            if not order_data:
                response_text = "I couldn't find any orders. Please check your order number or try again."
                self._add_to_history(sess, user_query, response_text)
                return response_text
            
            response_text = await self._llm_orchestrate_order(intent, user_query, order_data, sess)
            self._add_to_history(sess, user_query, response_text)
            
            # Context-Aware confirmation setup
            if self._is_asking_confirmation(response_text):
                if order_data["type"] == "single_order":
                    order = order_data["order"]
                    if intent == "order_cancel" and order.get("cancellable"):
                        sess["pending_action"] = {"action": "cancel", "order_id": order["id"]}
                    elif intent == "order_return" and order.get("returnable"):
                        sess["pending_action"] = {"action": "return", "order_id": order["id"]}
            
            return response_text
        except Exception as e:
            logger.error(f"Order intent error: {str(e)}")
            return "I'm having a little trouble looking up that order. Could you provide the order number?"

    async def _execute_pending_action(self, sess: dict, user_query: str) -> str:
        pending = sess.get("pending_action")
        if not pending: return "How can I help you today?"

        action, order_id = pending["action"], pending["order_id"]
        sess["pending_action"] = None # Clear state

        try:
            endpoint = "cancel" if action == "cancel" else "return"
            response = await self._http_client.post(
                f"{BACKEND_BASE_URL}/mock/orders/{endpoint}",
                params={"order_id": order_id},
                headers=API_KEY_HEADER
            )
            if response.status_code == 200:
                return response.json().get("message", "Request processed successfully.")
            return f"Error: {response.json().get('detail', 'Could not complete request.')}"
        except Exception as e:
            logger.error(f"Execution Error: {str(e)}")
            return "The system is busy. Please try again shortly."

    async def _fetch_order_data(self, intent, user_query, sess, product_context, x_api_key) -> Optional[dict]:
        # Extract ID
        order_match = re.search(r'(\d{3,10})', user_query)
        order_number = order_match.group(1) if order_match else sess.get("current_order_id")
        
        # Resolve IDs
        customer_id = sess.get("customer_id") or product_context.get("customer_id") or product_context.get("customer", {}).get("id")
        
        try:
            if order_number:
                res = await self._http_client.get(f"{BACKEND_BASE_URL}/mock/orders/status", params={"order_id": order_number}, headers=API_KEY_HEADER)
                if res.status_code == 200:
                    order = res.json()
                    sess["current_order_id"] = order["id"]
                    sess["last_discussed_order"] = order
                    return {"type": "single_order", "order": order}
            
            if customer_id:
                res = await self._http_client.get(f"{BACKEND_BASE_URL}/mock/orders/list", params={"customer_id": customer_id}, headers=API_KEY_HEADER)
                if res.status_code == 200:
                    data = res.json()
                    sess["customer_id"] = customer_id
                    return {"type": "order_list", "orders": data.get("orders", [])}
        except Exception as e:
            logger.error(f"Fetch Error: {str(e)}")
        return None

    # ============================================================
    # AI ORCHESTRATION
    # ============================================================
    async def _llm_orchestrate_order(self, intent, user_query, order_data, sess) -> str:
        import json
        history = "\n".join([f"User: {h['user']}\nBot: {h['assistant']}" for h in sess.get("conversation_history", [])[-2:]])
        
        prompt = f"""You are a helpful e-commerce customer assistant.
        HISTORY: {history}
        DATA: {json.dumps(order_data)}
        USER: {user_query}
        INSTRUCTIONS: Answer the user's specific request using the data provided. Be concise.
        """
        try:
            res = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": "You are a customer service assistant."}, {"role": "user", "content": prompt}],
                temperature=0.7
            )
            return res.choices[0].message.content.strip()
        except Exception:
            return ask_gemini(prompt)

    # ============================================================
    # PRODUCT Q&A (Restored functionality)
    # ============================================================
    async def _handle_product_question(self, user_query: str, product_context: dict) -> str:
        try:
            product_info = f"Product: {product_context.get('name')}. SKU: {product_context.get('sku')}. Price: ${product_context.get('price')}. Stock: {product_context.get('inStock')}"
            prompt = f"Answer this question about the product concisely:\n{user_query}\n\nDetails: {product_info}"
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "system", "content": "You are a helpful product assistant."}, {"role": "user", "content": prompt}],
                    max_tokens=300
                )
                return response.choices[0].message.content.strip()
            except OpenAIError:
                return ask_gemini(prompt)
        except Exception as e:
            logger.error(f"Product Q&A Error: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal processing error")

    # ============================================================
    # UTILITIES
    # ============================================================
    def _get_order_session(self, session_id: str) -> dict:
        if session_id not in self._order_sessions:
            self._order_sessions[session_id] = {
                "customer_id": None, "current_order_id": None,
                "last_discussed_order": None, "pending_action": None, "conversation_history": []
            }
        return self._order_sessions[session_id]

    def _add_to_history(self, sess: dict, user_msg: str, assistant_msg: str):
        if "conversation_history" not in sess: sess["conversation_history"] = []
        sess["conversation_history"].append({"user": user_msg, "assistant": assistant_msg})
        if len(sess["conversation_history"]) > 5: sess["conversation_history"].pop(0)

    def _is_asking_confirmation(self, response: str) -> bool:
        return any(p in response.lower() for p in ["shall i", "confirm", "yes/no", "would you like to"])

    def _is_confirmation(self, message: str) -> bool:
        return message.lower().strip() in ['yes', 'y', 'yeah', 'yep', 'confirm', 'proceed', 'do it']

    def _is_decline(self, message: str) -> bool:
        return message.lower().strip() in ['no', 'n', 'nope', 'nevermind', 'cancel']