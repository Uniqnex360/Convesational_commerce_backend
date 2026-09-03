import secrets
from typing import Any, Dict, List, Optional
from fastapi import HTTPException
from models.agent_schemas import (
    AgentBlock,
    AgentChatResponse,
    AgentIntent,
    ProductCard,
    ProductSearchResponse,
    RequirementSummary,
)
from .category_resolver import PureDynamicCategoryResolver, is_brand_request

from .compatibility_engine import CompatibilityEngine
from .comparison_engine import ComparisonEngine
from .explanation_engine import ExplanationEngine
from .fit_engine import FitEngine
from .intent_engine import IntentEngine
from .product_repository import ProductRepository
from .product_search import ProductSearchService
from .ranking_engine import RankingEngine
from .requirement_extractor import RequirementExtractor
from .response_composer import ResponseComposer
class ShopNexAIOrchestrator:
    def __init__(self) -> None:
        self.intent_engine = IntentEngine()
        self.products = ProductRepository()
        self.ranking = RankingEngine()
        self.requirement_extractor = RequirementExtractor()
        self.product_search = ProductSearchService(
            repository=self.products,
            ranking=self.ranking,
            extractor=self.requirement_extractor,
        )
        self.comparison = ComparisonEngine(self.ranking)
        self.fit = FitEngine()
        self.compatibility = CompatibilityEngine()
        self.explanations = ExplanationEngine()
        self.composer = ResponseComposer()
        self._session_requirements: Dict[str, RequirementSummary] = {}
        self.category_resolver = PureDynamicCategoryResolver()
    async def process_chat(
        self,
        message: str,
        session_id: Optional[str] = None,
        forced_intent: Optional[AgentIntent] = None,
        product_id: Optional[str] = None,
        product_ids: Optional[List[str]] = None,
        product_context: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
    ) -> AgentChatResponse:
        session_id = session_id or f"snx_{secrets.token_urlsafe(12)}"
        self.category_resolver.sync_catalog_categories(self.products.categories())
        intent = self.intent_engine.detect(message, forced_intent)
        extracted = await self.requirement_extractor.extract(
            message,
            known_categories=self.products.categories(),
            attribute_vocabulary=self.products.attribute_vocabulary(),
        )
        requirements = self._remember_requirements(session_id, extracted)
        if not requirements.category:
            resolved_cat = self.category_resolver.resolve(message)
            if resolved_cat:
                requirements.category = resolved_cat
        print(
            "CURRENT SESSION:",
            session_id,
            "REMEMBERED PRODUCT IDS:",
            requirements.product_ids,
        )
        print(
            "REMEMBERED REQUIREMENTS:",
            requirements.model_dump(),
        )
        if product_ids:
            requirements.product_ids = list(dict.fromkeys(product_ids))
        has_real_product = (
            self._has_real_product_context(product_context)
        )

        shopping_signals = (
            bool(requirements.category)
            or (
                requirements.budget_max is not None
                and requirements.budget_max > 0
            )
            or requirements.hard_constraints.get(
                "availability"
            ) is True
            or bool(requirements.preferences)
        )
        if intent == AgentIntent.product_question and not product_id and not has_real_product and shopping_signals:
            intent = AgentIntent.product_finder
        if (
            not product_id
            and len(requirements.product_ids) == 1
            and intent in (
                AgentIntent.product_question,
                AgentIntent.why_this_product,
                AgentIntent.check_fit,
                AgentIntent.find_alternatives,
            )
        ):
            product_id = requirements.product_ids[0]
        if is_brand_request(message):
            target_cat = requirements.category
            
            
            all_products = self.products.get_all()
            
            matching_products = [
                p for p in all_products
                if p.get("available") is not False
                and (
                    not target_cat
                    or str(p.get("category", "")).lower() == target_cat.lower()
                    or target_cat.lower() in str(p.get("title", "")).lower()
                )
            ]
            
            
            distinct_brands = list(dict.fromkeys(
                p.get("brand") for p in matching_products
                if p.get("brand") 
                and p.get("brand").strip().lower() not in ("e-commerce store", "unknown", "")
            ))
            
            if distinct_brands:
                cat_label = target_cat or "catalog"
                brand_list_text = (
                    f"Here are the available brands for **{cat_label}**:\n\n"
                    + "\n".join(f"• {b}" for b in distinct_brands)
                )
                
                
                cards = [self._card(p) for p in matching_products[:6]]
                
                return AgentChatResponse(
                    session_id=session_id,
                    intent=intent.value,
                    message=brand_list_text,
                    requirements=requirements,
                    blocks=[
                        AgentBlock(
                            type="product_recommendations",
                            data={
                                "products": [c.model_dump() for c in cards],
                                "total": len(cards),
                                "exact_match": True,
                            },
                        )
                    ],
                )
        if intent in (AgentIntent.shopping_agent, AgentIntent.product_finder):
            result = await self.search_products(message, requirements, limit=10)
            if result.products:
                return self.composer.recommendations(
                    session_id, intent, requirements, result
                )
            return self.composer.zero_results(
                session_id, intent, requirements, query=message
            )
        if intent == AgentIntent.find_alternatives:
            current_product = self._get_product(product_id, product_context)
            search_text = message
            if current_product:
                search_text = f"{current_product.get('title', '')} {current_product.get('category', '')} {message}"
            result = await self.search_products(
                search_text,
                requirements,
                limit=10,
                exclude_ids=[product_id] if product_id else [],
                strict=False,
            )
            return self.composer.recommendations(
                session_id, intent, requirements, result
            )
        if intent == AgentIntent.compare_products:
            ids = product_ids or requirements.product_ids
            if len(ids) < 2:
                return AgentChatResponse(
                    session_id=session_id,
                    intent=intent.value,
                    message="Please select at least two products to compare.",
                    requirements=requirements,
                    blocks=[AgentBlock(type="comparison_request", data={})],
                )
            comparison = await self.compare_products(ids, requirements,session_id=session_id)
            return self.composer.comparison(
                session_id, requirements, comparison
            )
        if intent == AgentIntent.why_this_product:
            product = self._get_product(product_id, product_context)
            if not product:
                return self._missing_product_response(session_id, intent, requirements)
            scored = self.ranking.rank([product], requirements, strict=False)[0]
            explanation = await self.explanations.explain_recommendation(
                scored, scored.get("reasons", []), requirements.model_dump()
            )
            return self.composer.why_product(
                session_id=session_id,
                requirements=requirements,
                product=self._card(scored),
                evidence=scored.get("reasons", []),
                message=explanation,
            )
        if intent == AgentIntent.check_fit:
            product = self._get_product(product_id, product_context)
            if not product:
                return self._missing_product_response(session_id, intent, requirements)
            fit_result = self.fit.check(product, requirements)
            return self.composer.fit_result(
                session_id=session_id,
                requirements=requirements,
                product=self._card(product),
                result=fit_result,
                message=self._fit_message(fit_result),
            )
        if intent == AgentIntent.check_compatibility:
            ids = product_ids or requirements.product_ids
            if len(ids) < 2:
                return AgentChatResponse(
                    session_id=session_id,
                    intent=intent.value,
                    message="Please provide two product IDs to check compatibility.",
                    requirements=requirements,
                    blocks=[AgentBlock(type="compatibility_request", data={})],
                )
            result = self.check_compatibility(ids[0], ids[1])
            return self.composer.compatibility_result(
                session_id=session_id,
                requirements=requirements,
                result=result,
                message=self._compatibility_message(result),
            )
        if intent == AgentIntent.product_question:
            if len(requirements.product_ids) >= 2:
                products = self.products.get_many(
                    requirements.product_ids
                )
                if len(products) < 2:
                    return AgentChatResponse(
                        session_id=session_id,
                        intent=intent.value,
                        message=(
                            "I could not find both compared products "
                            "in the catalog."
                        ),
                        requirements=requirements,
                    )
                product_messages = []
                feature_products = []
                for product in products:
                    product_id_value = str(
                        product.get("id", "")
                    )
                    product_title = str(
                        product.get("title")
                        or product.get("name")
                        or product_id_value
                    )
                    features: Dict[str, Any] = {}
                    for field_name in (
                        "attributes",
                        "specifications",
                        "features",
                    ):
                        field_value = product.get(field_name)
                        if isinstance(field_value, dict):
                            features.update(field_value)
                    feature_products.append(
                        {
                            "id": product_id_value,
                            "title": product_title,
                            "features": features,
                        }
                    )
                    if features:
                        feature_text = "; ".join(
                            f"{key}: {value}"
                            for key, value in features.items()
                            if value is not None and value != ""
                        )
                        product_messages.append(
                            f"{product_title}: {feature_text}"
                        )
                    else:
                        product_messages.append(
                            f"{product_title}: "
                            "Feature information is not available "
                            "in the catalog."
                        )
                return AgentChatResponse(
                    session_id=session_id,
                    intent=intent.value,
                    message=(
                        "Here are the verified features of the "
                        "compared products:\n\n"
                        + "\n\n".join(product_messages)
                    ),
                    requirements=requirements,
                    blocks=[
                        AgentBlock(
                            type="product_features",
                            data={
                                "products": feature_products,
                            },
                        )
                    ],
                )
            product = self._get_product(
                product_id,
                product_context,
            )
            if product:
                response = (
                    await self.explanations.answer_product_question(
                        product,
                        message,
                    )
                )
                return self.composer.product_question(
                    session_id=session_id,
                    requirements=requirements,
                    product=self._card(product),
                    message=response,
                )
            return AgentChatResponse(
                session_id=session_id,
                intent=intent.value,
                message=(
                    "Please provide a product ID or open this "
                    "assistant from a product page."
                ),
                requirements=requirements,
            )
        try:
            from services.chatbot_service import ChatbotService
            legacy_response = await ChatbotService().process_chat_message(
                message, product_context or {}, session_id, api_key
            )
            return self.composer.support_text(
                session_id=session_id,
                intent=intent,
                requirements=requirements,
                message=legacy_response,
            )
        except Exception:
            return AgentChatResponse(
                session_id=session_id,
                intent=intent.value,
                message="I can help with that, but the support service is temporarily unavailable.",
                requirements=requirements,
            )
    async def search_products(
        self,
        query: str,
        requirements: Optional[RequirementSummary] = None,
        limit: int = 10,
        exclude_ids: Optional[List[str]] = None,
        strict: bool = True,
    ) -> ProductSearchResponse:
        return await self.product_search.search(
            query=query,
            requirements=requirements,
            limit=limit,
            strict=strict,
            exclude_ids=exclude_ids,
        )
    async def compare_products(
        self,
        product_ids: List[str],
        requirements: Optional[RequirementSummary] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        normalized_ids = list(
            dict.fromkeys(
                str(product_id).strip()
                for product_id in product_ids
                if str(product_id).strip()
            )
        )
        if len(normalized_ids) < 2:
            raise HTTPException(
                status_code=400,
                detail="At least two products are required for comparison",
            )
        products = self.products.get_many(normalized_ids)
        if len(products) < 2:
            raise HTTPException(
                status_code=404,
                detail="At least two products could not be found",
            )
        if session_id:
            remembered = (
                self._session_requirements.get(session_id)
                or requirements
                or RequirementSummary()
            )
            remembered.product_ids = normalized_ids
            self._session_requirements[session_id] = remembered
            print(
                "COMPARISON MEMORY SAVED:",
                session_id,
                normalized_ids,
            )
        return self.comparison.compare(
            products,
            requirements,
        )
    async def explain_product(
        self,
        product_id: str,
        requirements: Optional[RequirementSummary] = None,
    ) -> AgentChatResponse:
        requirements = requirements or RequirementSummary()
        product = self.products.get(product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        scored = self.ranking.rank([product], requirements, strict=False)[0]
        message = await self.explanations.explain_recommendation(
            scored, scored.get("reasons", []), requirements.model_dump()
        )
        return AgentChatResponse(
            session_id=f"snx_{secrets.token_urlsafe(12)}",
            intent=AgentIntent.why_this_product.value,
            message=message,
            requirements=requirements,
            blocks=[AgentBlock(type="why_this_product", data={"product": self._card(scored).model_dump(), "evidence": scored.get("reasons", [])})],
        )
    def fit_product(self, product_id: str, requirements: RequirementSummary) -> Dict[str, Any]:
        product = self.products.get(product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return {"product": self._card(product).model_dump(), **self.fit.check(product, requirements)}
    def check_compatibility(self, product_a_id: str, product_b_id: str) -> Dict[str, Any]:
        product_a = self.products.get(product_a_id)
        product_b = self.products.get(product_b_id)
        if not product_a or not product_b:
            raise HTTPException(status_code=404, detail="One or both products were not found")
        return {
            "product_a": self._card(product_a).model_dump(),
            "product_b": self._card(product_b).model_dump(),
            **self.compatibility.check(product_a, product_b),
        }
    def _remember_requirements(self, session_id: str, current: RequirementSummary) -> RequirementSummary:
        previous = self._session_requirements.get(session_id)
        if not previous:
            self._session_requirements[session_id] = current
            return current
        data = previous.model_dump()
        current_data = current.model_dump()
        data["category"] = current_data.get("category")
        for key in ( "quantity", "budget_min", "budget_max", "currency", "use_case"):
            if current_data.get(key) is not None:
                data[key] = current_data[key]
        data["hard_constraints"].update(current_data.get("hard_constraints", {}))
        data["preferences"].update(current_data.get("preferences", {}))
        data["product_ids"] = list(dict.fromkeys(data.get("product_ids", []) + current_data.get("product_ids", [])))
        merged = RequirementSummary.model_validate(data)
        self._session_requirements[session_id] = merged
        return merged
    @staticmethod
    def _has_real_product_context(product_context:Optional[Dict[str,Any]],)->bool:
        if not product_context:
            return False
        product_id=(product_context.get('productId') or product_context.get('product_id')or product_context.get('id'))
        if product_id and str(product_id).strip():
            return True
        product_name=str(product_context.get('name') or product_context.get('title') or "").strip().casefold()
        placeholder_names={
              "",
            "product",
            "loading...",
            "unknown product",
            "e-commerce store",
            "ecommerce store",
            "shopify",
        }
        return product_name not in placeholder_names
    def _get_product(self, product_id: Optional[str], product_context: Optional[Dict[str, Any]]):
        if product_id:
            product = self.products.get(product_id)
            if product:
                return product
        if self._has_real_product_context(
            product_context
        ):
            return self.products.normalize(
                product_context
            )
        return None
    @staticmethod
    def _card(product: Dict[str, Any]) -> ProductCard:
        return ProductCard(
            id=str(product.get("id", "")),
            title=product.get("title") or "Untitled product",
            price=product.get("price"),
            currency=product.get("currency"),
            brand=product.get("brand"),
            image=product.get("image"),
            handle=product.get("handle"),
            product_url=product.get("product_url"),
            category=product.get("category"),
            available=product.get("available"),
            score=product.get("score"),
            reasons=product.get("reasons", []),
            compromises=product.get("compromises", []),
            attributes=product.get("attributes", {}),
        )
    @staticmethod
    def _missing_product_response(session_id: str, intent: AgentIntent, requirements: RequirementSummary):
        return AgentChatResponse(
            session_id=session_id,
            intent=intent.value,
            message="Please provide a product ID or open this assistant from a product page.",
            requirements=requirements,
        )
    @staticmethod
    def _fit_message(result: Dict[str, Any]) -> str:
        messages = {
            "fit": "This product matches the requirements provided.",
            "partial": "This product is a partial match, but some information is missing.",
            "not_fit": "This product does not satisfy all of the requirements.",
            "unknown": "I don't have enough product information to confirm the fit.",
        }
        return messages[result.get("status", "unknown")]
    @staticmethod
    def _compatibility_message(result: Dict[str, Any]) -> str:
        return {
            "compatible": "These products are compatible according to the catalog data.",
            "incompatible": "These products are not compatible according to the catalog data.",
            "unknown": "I cannot confirm compatibility because the catalog lacks sufficient evidence.",
        }.get(result.get("status"), "Compatibility is unknown.")
