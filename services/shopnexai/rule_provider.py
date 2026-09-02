import json
import os
import re
from typing import Any, Dict, List


class FitRuleProvider:
   

    def get_rules(self, category: str | None) -> List[Dict[str, Any]]:
        if not category:
            return []

        wanted_category = self._normalize(category)
        rules: List[Dict[str, Any]] = []

        raw_rules = os.getenv("SHOPNEXAI_FIT_RULES_JSON")

        if raw_rules:
            try:
                configured_rules = json.loads(raw_rules)

                if isinstance(configured_rules, dict):
                    configured_rules = [configured_rules]

                if isinstance(configured_rules, list):
                    rules.extend(
                        rule
                        for rule in configured_rules
                        if isinstance(rule, dict)
                        and self._normalize(
                            rule.get("category", "")
                        ) == wanted_category
                    )

            except json.JSONDecodeError:
                pass

        try:
            from models.schemas import fit_rule

            for document in fit_rule.objects:
                if self._normalize(document.category) != wanted_category:
                    continue

                rules.append(
                    {
                        "category": document.category,
                        "requirement_attribute": (
                            document.requirement_attribute
                        ),
                        "product_attribute": (
                            document.product_attribute
                        ),
                        "relation": document.relation,
                        "min_offset": document.min_offset,
                        "max_offset": document.max_offset,
                        "required": document.required,
                        "explanation_template": (
                            document.explanation_template
                        ),
                    }
                )

        except Exception:
            # ShopNexAI remains usable when MongoDB or the
            # optional fit_rule collection is unavailable.
            pass

        return rules

    @staticmethod
    def _normalize(value: Any) -> str:
        return re.sub(
            r"[^a-z0-9]",
            "",
            str(value or "").lower(),
        )
