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
        """
        Main chat handler. Detects intent and routes to:
          - Order management (status/cancel/return)
          - Product Q&A (existing flow)
        """
        if not session_id:
            session_id = "default-session"
        intent = self._classify_intent(user_query, product_context)
        if intent in ("order_status", "order_cancel", "order_return") and x_api_key:
            return await self._handle_order_intent(
                intent, user_query, session_id, product_context, x_api_key
            )
        return await self._handle_product_question(user_query, product_context)
    def _classify_intent(self, user_query: str, product_context: dict) -> str:
        """
        Classify user intent.
        Returns: 'order_status' | 'order_cancel' | 'order_return' | 'product'
        """
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
            "did it ship", "arrived yet", "where is my package"
        ]
        if any(kw in msg for kw in status_keywords):
            return "order_status"
        
        # ✅ NEW: Detect standalone order numbers (e.g., "1001", "#1001", "order 1001")
        # Matches: just digits, with #, or with "order" prefix
        order_number_pattern = r'^\s*(?:#|order\s*(?:number\s*)?(?:\s*is\s*)?)?(\d{3,10})\s*$'
        if re.match(order_number_pattern, msg):
            return "order_status"
        
        # ✅ NEW: Detect order number + email in same message
        if re.search(r'\d{3,10}', msg) and ('@' in msg or 'email' in msg):
            return "order_status"
        
        # ✅ NEW: Detect order number with "order" keyword
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
        """Route order intents to the orchestration layer"""
        from services.order_intent_handler import (
            handle_order_status_query,
            handle_order_cancel,
            handle_order_return,
        )
        context_with_customer = dict(product_context)
        if not context_with_customer.get("customer_id"):
            context_with_customer["customer_id"] = None
        try:
            if intent == "order_status":
                result = await handle_order_status_query(
                    user_query, session_id, context_with_customer, x_api_key
                )
            elif intent == "order_cancel":
                result = await handle_order_cancel(
                    user_query, session_id, context_with_customer, x_api_key
                )
            elif intent == "order_return":
                result = await handle_order_return(
                    user_query, session_id, context_with_customer, x_api_key
                )
            else:
                return "I'm not sure how to help with that."
            reply = result.get("reply_text", "I couldn't process that request.")
            if result.get("escalate"):
                reply += "\n\n[ESCALATE TO HUMAN AGENT]"
            return reply
        except Exception as e:
            print(f"Order intent handler error: {e}")
            import traceback
            traceback.print_exc()
            return "I'm having trouble looking up your order right now. Please try again in a moment."
    async def _handle_product_question(
        self,
        user_query: str,
        product_context: dict,
    ) -> str:
        """Existing product Q&A flow with OpenAI/Gemini fallback"""
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
You are an AI assistant for an e-commerce website. Your task is to provide clear and relevant answers based on the given product details.
1. Answer concisely based only on the product details provided.
2. If the user asks about orders, cancellations, returns, or tracking, respond that you can help with that and ask for their order number.
3. Avoid raw data dumps—only provide direct human-readable responses.
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