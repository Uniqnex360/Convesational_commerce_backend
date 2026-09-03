import re
from typing import Any, Dict, List, Optional

from models.agent_schemas import RequirementSummary


class RankingEngine:
    def rank(
        self,
        products: List[Dict[str, Any]],
        requirements: RequirementSummary,
        strict: bool = True,
        exclude_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        excluded = set(exclude_ids or [])
        ranked = []

        for product in products:
            if str(product.get("id")) in excluded:
                continue

            failures = self._hard_failures(
                product,
                requirements,
            )

            if strict and failures:
                continue

            score, reasons, compromises = self._score(
                product,
                requirements,
                failures,
            )

            ranked.append(
                {
                    **product,
                    "score": round(score, 1),
                    "reasons": reasons,
                    "compromises": compromises,
                }
            )

        ranked.sort(
            key=lambda item: item.get("score", 0),
            reverse=True,
        )

        return ranked

    def _hard_failures(
        self,
        product: Dict[str, Any],
        requirements: RequirementSummary,
    ) -> List[str]:
        failures: List[str] = []

        price = self._number(product.get("price"))

        max_budget = requirements.budget_max
        min_budget = requirements.budget_min
        if requirements.category:
            requested_category = self._normalize_text(
                requirements.category
            )

            product_category = self._normalize_text(
                product.get("category")
            )

            if requested_category != product_category:
                failures.append(
                    "Category does not match"
                )
        if max_budget is None:
            max_budget = self._number(
                requirements.hard_constraints.get(
                    "budget_max"
                )
            )

        if min_budget is None:
            min_budget = self._number(
                requirements.hard_constraints.get(
                    "budget_min"
                )
            )

        if (
            max_budget is not None
            and price is not None
            and price > max_budget
        ):
            failures.append(
                f"Price is above {max_budget:g}"
            )

        if (
            min_budget is not None
            and price is not None
            and price < min_budget
        ):
            failures.append(
                f"Price is below {min_budget:g}"
            )

        if (
            requirements.hard_constraints.get(
                "availability"
            ) is True
            and not product.get("available")
        ):
            failures.append(
                "Product is unavailable"
            )

        for key, expected in (
            requirements.hard_constraints.items()
        ):
            if key in {
                "budget_max",
                "budget_min",
                "availability",
            }:
                continue

            if isinstance(expected, dict):
                actual_num = self._number(self._attribute(product, key))
                if actual_num is not None:
                    if "max" in expected and actual_num > expected["max"]:
                        failures.append(f"{key} is above {expected['max']:g}")
                    if "min" in expected and actual_num < expected["min"]:
                        failures.append(f"{key} is below {expected['min']:g}")
                continue

            actual = self._attribute(product, key)


            if (
                actual is not None
                and not self._matches(actual, expected)
            ):
                failures.append(
                    f"{key} does not match"`
                )

        return failures
    @staticmethod
    def _normalize_text(value: Any) -> str:
        return re.sub(
            r"[^a-z0-9]",
            "",
            str(value or "").lower(),
        )
    def _score(
        self,
        product: Dict[str, Any],
        requirements: RequirementSummary,
        failures: List[str],
    ):
        score = 55.0
        reasons: List[str] = []
        compromises = list(failures)

        price = self._number(product.get("price"))

        if product.get("available"):
            score += 10
            reasons.append("Currently available")
        else:
            compromises.append(
                "Availability is not confirmed"
            )

        if requirements.category:
            requested_category = self._normalize_text(
                requirements.category
            )

            product_category = self._normalize_text(
                product.get("category")
            )

            if (
                requested_category
                and requested_category == product_category
            ):
                score += 15
                reasons.append(
                    "Matches the requested category"
                )
            else:
                score -= 10
                compromises.append(
                    "Category is not an exact match"
                )

        max_budget = requirements.budget_max

        if max_budget is None:
            max_budget = self._number(
                requirements.hard_constraints.get(
                    "budget_max"
                )
            )

        if (
            max_budget is not None
            and price is not None
        ):
            if price <= max_budget:
                score += 15
                reasons.append(
                    "Within your budget"
                )
            else:
                score -= 15
                compromises.append(
                    "Above your budget"
                )

        for key, expected in (
            requirements.preferences.items()
        ):
            actual = self._attribute(product, key)

            if (
                actual is not None
                and self._matches(actual, expected)
            ):
                score += 5
                reasons.append(
                    f"Matches your {key} preference"
                )
            elif actual is not None:
                compromises.append(
                    f"{key} preference is not an exact match"
                )

        score -= min(
            len(failures) * 20,
            50,
        )

        return (
            max(0.0, min(100.0, score)),
            reasons,
            compromises,
        )

    @staticmethod
    def _attribute(
        product: Dict[str, Any],
        key: str,
    ) -> Any:
        normalized_key = re.sub(
            r"[^a-z0-9]",
            "",
            key.lower(),
        )

        for candidate, value in (
            product.get("attributes", {}).items()
        ):
            normalized_candidate = re.sub(
                r"[^a-z0-9]",
                "",
                str(candidate).lower(),
            )

            if normalized_candidate == normalized_key:
                return value

        for candidate in (
            key,
            key.lower(),
            key.replace("_", ""),
        ):
            if candidate in product:
                return product[candidate]

        return None

    @staticmethod
    def _matches(
        actual: Any,
        expected: Any,
    ) -> bool:
        if isinstance(actual, list):
            return any(
                RankingEngine._matches(
                    item,
                    expected,
                )
                for item in actual
            )

        return (
            str(expected).lower()
            in str(actual).lower()
        )

    @staticmethod
    def _number(
        value: Any,
    ) -> Optional[float]:
        if value is None:
            return None

        if isinstance(value, (int, float)):
            return float(value)

        match = re.search(
            r"-?\d[\d,]*(?:\.\d+)?",
            str(value),
        )

        if not match:
            return None

        return float(
            match.group(0).replace(",", "")
        )
