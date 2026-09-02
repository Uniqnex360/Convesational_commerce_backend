"""Response composition for ShopNexAI.

Commerce services return verified data. This module converts that data into a
stable response contract for the frontend without making new product claims.
"""

from typing import Any, Dict, List, Optional

from models.agent_schemas import (
    AgentBlock,
    AgentChatResponse,
    AgentIntent,
    ProductCard,
    ProductSearchResponse,
    RequirementSummary,
)


class ResponseComposer:

    def recommendations(
        self,
        session_id: str,
        intent: AgentIntent | str,
        requirements: RequirementSummary,
        result: ProductSearchResponse,
    ) -> AgentChatResponse:
        intent_value = self._intent_value(intent)
        if result.products:
            phrase = "best matches" if result.exact_match else "closest matches"
            block_type = (
                "alternative_products"
                if intent_value == AgentIntent.find_alternatives.value
                else "product_recommendations"
            )
            return self._response(
                session_id=session_id,
                intent=intent_value,
                message=f"Here are the {phrase} for your request.",
                requirements=requirements,
                blocks=[AgentBlock(type=block_type, data=result.model_dump())],
            )
        return self.zero_results(session_id, intent, requirements)

    def zero_results(
        self,
        session_id: str,
        intent: AgentIntent | str,
        requirements: RequirementSummary,
        query: Optional[str] = None,
    ) -> AgentChatResponse:
        return self._response(
            session_id=session_id,
            intent=self._intent_value(intent),
            message="I couldn't find an exact match. You can try a different category, budget, or preference.",
            requirements=requirements,
            blocks=[
                AgentBlock(
                    type="zero_results",
                    data={"query": query, "suggestion": "Relax one or more filters."},
                )
            ],
        )

    def comparison(
        self,
        session_id: str,
        requirements: RequirementSummary,
        comparison_data: Dict[str, Any],
    ) -> AgentChatResponse:
        return self._response(
            session_id=session_id,
            intent=AgentIntent.compare_products.value,
            message="Here is the product comparison.",
            requirements=requirements,
            blocks=[AgentBlock(type="comparison", data=comparison_data)],
        )

    def why_product(
        self,
        session_id: str,
        requirements: RequirementSummary,
        product: ProductCard,
        evidence: List[Any],
        message: str,
    ) -> AgentChatResponse:
        return self._response(
            session_id=session_id,
            intent=AgentIntent.why_this_product.value,
            message=message,
            requirements=requirements,
            blocks=[
                AgentBlock(
                    type="why_this_product",
                    data={"product": product.model_dump(), "evidence": evidence},
                )
            ],
        )

    def fit_result(
        self,
        session_id: str,
        requirements: RequirementSummary,
        product: ProductCard,
        result: Dict[str, Any],
        message: str,
    ) -> AgentChatResponse:
        return self._response(
            session_id=session_id,
            intent=AgentIntent.check_fit.value,
            message=message,
            requirements=requirements,
            blocks=[
                AgentBlock(
                    type="fit_result",
                    data={"product": product.model_dump(), **result},
                )
            ],
        )

    def compatibility_result(
        self,
        session_id: str,
        requirements: RequirementSummary,
        result: Dict[str, Any],
        message: str,
    ) -> AgentChatResponse:
        return self._response(
            session_id=session_id,
            intent=AgentIntent.check_compatibility.value,
            message=message,
            requirements=requirements,
            blocks=[AgentBlock(type="compatibility_result", data=result)],
        )

    def product_question(
        self,
        session_id: str,
        requirements: RequirementSummary,
        product: ProductCard,
        message: str,
    ) -> AgentChatResponse:
        return self._response(
            session_id=session_id,
            intent=AgentIntent.product_question.value,
            message=message,
            requirements=requirements,
            blocks=[AgentBlock(type="product", data={"product": product.model_dump()})],
        )

    def support_text(
        self,
        session_id: str,
        intent: AgentIntent | str,
        requirements: RequirementSummary,
        message: str,
    ) -> AgentChatResponse:
        return self._response(
            session_id=session_id,
            intent=self._intent_value(intent),
            message=message,
            requirements=requirements,
            blocks=[AgentBlock(type="support_text", data={})],
        )

    def missing_product(
        self,
        session_id: str,
        intent: AgentIntent | str,
        requirements: RequirementSummary,
    ) -> AgentChatResponse:
        return self._response(
            session_id=session_id,
            intent=self._intent_value(intent),
            message="Please provide a product ID or open this assistant from a product page.",
            requirements=requirements,
        )

    @staticmethod
    def _response(
        session_id: str,
        intent: str,
        message: str,
        requirements: Optional[RequirementSummary] = None,
        blocks: Optional[List[AgentBlock]] = None,
    ) -> AgentChatResponse:
        return AgentChatResponse(
            session_id=session_id,
            intent=intent,
            message=message,
            requirements=requirements,
            blocks=blocks or [],
        )

    @staticmethod
    def _intent_value(intent: AgentIntent | str) -> str:
        return intent.value if isinstance(intent, AgentIntent) else str(intent)
