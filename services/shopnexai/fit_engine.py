import re
from typing import Any, Dict, Set

from models.agent_schemas import RequirementSummary

from .rule_provider import FitRuleProvider


class FitEngine:

    def __init__(self, rules: FitRuleProvider | None = None) -> None:
        self.rules = rules or FitRuleProvider()

    def check(self, product: Dict[str, Any], requirements: RequirementSummary) -> Dict[str, Any]:
        evidence = []
        failures = []
        unknowns = []
        evaluated: Set[str] = set()

        if requirements.budget_max is not None:
            if product.get("price") is None:
                unknowns.append("Product price is missing")
            elif float(product["price"]) <= requirements.budget_max:
                evidence.append(self._evidence("Within your budget", "price", 0.99))
            else:
                failures.append("Price is above your budget")

        if requirements.hard_constraints.get("availability") is True:
            if product.get("available"):
                evidence.append(self._evidence("Availability is confirmed", "availability", 0.95))
            else:
                failures.append("Product is not currently available")

        # Category-specific calculations are loaded as data. For example, a
        # merchant can configure a rule that maps surface_height to
        # seat_height without adding a new hardcoded Python condition.
        for rule in self.rules.get_rules(requirements.category):
            req_key = rule.get("requirement_attribute")
            product_key = rule.get("product_attribute")
            if not req_key or not product_key:
                continue
            expected = self._requirement_value(requirements, req_key)
            actual = self._attribute(product, product_key)
            evaluated.add(req_key)
            if expected is None or actual is None:
                unknowns.append(f"{req_key} or {product_key} is not specified")
                continue
            result = self._apply_rule(rule, expected, actual)
            if result is True:
                evidence.append(
                    self._evidence(
                        rule.get("explanation_template")
                        or f"{product_key} satisfies {req_key}",
                        product_key,
                        0.93,
                    )
                )
            elif result is False and rule.get("required", True):
                failures.append(f"Product does not satisfy {req_key}")

        # for key, expected in {**requirements.hard_constraints, **requirements.preferences}.items():
        #     if key in {"budget_max", "budget_min", "availability"} or key in evaluated:
        #         continue
        #     actual = self._attribute(product, key)
        #     if actual is None:
        #         unknowns.append(f"{key} is not specified")
        #     elif self._matches(actual, expected):
        #         evidence.append(self._evidence(f"Matches {key}: {expected}", key, 0.85))
        #     elif key in requirements.hard_constraints:
        #         failures.append(f"Does not match required {key}")
        for key, expected in {**requirements.hard_constraints, **requirements.preferences}.items():
            if key in {"budget_max", "budget_min", "availability"} or key in evaluated:
                continue
            actual = self._attribute(product, key)
            if actual is None:
                unknowns.append(f"{key} is not specified")
                continue
            if isinstance(expected, dict):
                actual_num = self._number(actual)
                if actual_num is None:
                    unknowns.append(f"{key} is not specified")
                    continue
                ok = True
                if "max" in expected and actual_num > expected["max"]:
                    ok = False
                if "min" in expected and actual_num < expected["min"]:
                    ok = False
                if ok:
                    evidence.append(self._evidence(f"{key} is within range: {actual_num:g}", key, 0.9))
                elif key in requirements.hard_constraints:
                    failures.append(f"Does not match required {key}")
                continue
            if self._matches(actual, expected):
                evidence.append(self._evidence(f"Matches {key}: {expected}", key, 0.85))
            elif key in requirements.hard_constraints:
                failures.append(f"Does not match required {key}")

        checks = len(evidence) + len(failures) + len(unknowns)
        score = round((len(evidence) / checks) * 100) if checks else 0
        if failures:
            status = "not_fit"
        elif unknowns and evidence:
            status = "partial"
        elif unknowns:
            status = "unknown"
        else:
            status = "fit" if evidence else "unknown"

        return {
            "status": status,
            "score": score,
            "evidence": evidence,
            "missing_information": unknowns,
            "conflicts": failures,
        }

    @staticmethod
    def _apply_rule(rule: Dict[str, Any], expected: Any, actual: Any):
        relation = rule.get("relation")
        if relation == "range_from_input":
            input_value = FitEngine._number(expected)
            product_value = FitEngine._number(actual)
            min_offset = FitEngine._number(rule.get("min_offset"))
            max_offset = FitEngine._number(rule.get("max_offset"))
            if None in (input_value, product_value, min_offset, max_offset):
                return None
            return input_value + min_offset <= product_value <= input_value + max_offset
        if relation == "equals":
            return FitEngine._matches(actual, expected)
        if relation == "contains":
            return str(expected).lower() in str(actual).lower()
        return None

    @staticmethod
    def _requirement_value(requirements: RequirementSummary, key: str):
        if key in requirements.hard_constraints:
            return requirements.hard_constraints[key]
        if key in requirements.preferences:
            return requirements.preferences[key]
        return getattr(requirements, key, None)

    @staticmethod
    def _attribute(product: Dict[str, Any], key: str) -> Any:
        normalized = re.sub(r"[^a-z0-9]", "", key.lower())
        for name, value in product.get("attributes", {}).items():
            if re.sub(r"[^a-z0-9]", "", str(name).lower()) == normalized:
                return value
        return product.get(key)

    @staticmethod
    def _number(value: Any):
        if isinstance(value, dict):
            value = value.get("value")
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        match = re.search(r"-?\d[\d,]*(?:\.\d+)?", str(value))
        return float(match.group(0).replace(",", "")) if match else None

    @staticmethod
    def _matches(actual: Any, expected: Any) -> bool:
        if isinstance(actual, list):
            return any(FitEngine._matches(item, expected) for item in actual)
        return str(expected).lower() in str(actual).lower()

    @staticmethod
    def _evidence(claim: str, attribute: str, confidence: float) -> Dict[str, Any]:
        return {
            "claim": claim,
            "source": {"type": "product_attribute", "attribute": attribute},
            "confidence": confidence,
        }
