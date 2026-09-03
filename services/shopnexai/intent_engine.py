import re
from typing import Optional

from models.agent_schemas import AgentIntent


class IntentEngine:
  

    def detect(
        self,
        message: str,
        forced_intent: Optional[AgentIntent] = None,
    ) -> AgentIntent:
        if forced_intent:
            return forced_intent

        text = message.lower().strip()

        rules = [
            (
                AgentIntent.check_compatibility,
                (
                    "compatible",
                    "compatibility",
                    "work with",
                    "connect to",
                ),
            ),
            (
                AgentIntent.check_fit,
                (
                    "fit",
                    "suitable for",
                    "work for me",
                    "will it fit",
                ),
            ),
            (
                AgentIntent.compare_products,
                (
                    "compare",
                    "comparison",
                    "versus",
                    " vs ",
                    "which one is better",
                ),
            ),
            (
                AgentIntent.why_this_product,
                (
                    "why this",
                    "why did you recommend",
                    "why recommend",
                ),
            ),
            (
                AgentIntent.find_alternatives,
                (
                    "alternative",
                    "alternatives",
                    "similar product",
                    "closest match",
                ),
            ),
            (
                AgentIntent.order,
                (
                    "cancel my order",
                    "order status",
                    "track my order",
                    "where is my order",
                ),
            ),
            (
                AgentIntent.delivery,
                (
                    "delivery",
                    "shipping",
                    "warranty",
                    "return",
                ),
            ),
            (
                AgentIntent.billing,
                (
                    "billing",
                    "payment",
                    "invoice",
                    "charged",
                ),
            ),
            (
                AgentIntent.feedback,
                (
                    "feedback",
                    "suggestion",
                    "complaint",
                ),
            ),
        ]

        for intent, phrases in rules:
            if any(phrase in text for phrase in phrases):
                return intent

        if re.search(
            r"\b(show|find|recommend|need|looking for|search|any other|other options|different)\b",
            text,
        ):
            return AgentIntent.shopping_agent

        return AgentIntent.product_question