import json
from typing import Any, Dict, List, Optional

from .llm_client import LLMClient


class ExplanationEngine:
    def __init__(self, llm: Optional[LLMClient] = None) -> None:
        self.llm = llm or LLMClient()

    async def explain_recommendation(
        self,
        product: Dict[str, Any],
        reasons: List[str],
        requirements: Dict[str, Any],
    ) -> str:
        fallback = self._fallback(product, reasons)
        response = await self.llm.text_completion(
            system_prompt=(
                "You explain ecommerce recommendations. Use only the supplied "
                "product facts and reasons. Do not add unsupported claims, "
                "prices, dimensions, availability, or compatibility."
            ),
            user_prompt=json.dumps(
                {"product": product, "reasons": reasons, "requirements": requirements},
                default=str,
            ),
        )
        return response or fallback

    async def answer_product_question(
        self,
        product: Dict[str, Any],
        question: str,
    ) -> str:
        fallback = self._question_fallback(product, question)
        response = await self.llm.text_completion(
            system_prompt=(
                "You are a product assistant. Answer only from the supplied "
                "catalog JSON. If the information is missing, say that it is "
                "not specified. Never invent product facts. Keep the answer concise."
            ),
            user_prompt=json.dumps(
                {"question": question, "catalog_product": product},
                default=str,
            ),
        )
        return response or fallback

    @staticmethod
    def _fallback(product: Dict[str, Any], reasons: List[str]) -> str:
        title = product.get("title", "This product")
        if reasons:
            return f"{title} is recommended because " + ", ".join(reasons).lower() + "."
        return f"{title} is one of the closest matches to your request."

    @staticmethod
    def _question_fallback(product: Dict[str, Any], question: str) -> str:
        text = question.lower()
        title = product.get("title", "This product")
        if "price" in text or "cost" in text:
            if product.get("price") is not None:
                return f"{title} is listed at {product['price']} {product.get('currency', '')}.".strip()
        if "stock" in text or "available" in text:
            return f"{title} is currently {'available' if product.get('available') else 'not available'} according to the catalog."
        if "brand" in text and product.get("brand"):
            return f"The brand is {product['brand']}."
        if "sku" in text and product.get("sku"):
            return f"The SKU is {product['sku']}."
        return f"I don't have enough catalog information to answer that question about {title}."
