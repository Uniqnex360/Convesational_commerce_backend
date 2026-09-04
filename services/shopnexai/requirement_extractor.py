import re
from typing import Any, Dict, List, Optional
from models.agent_schemas import RequirementSummary
from .llm_client import LLMClient
class RequirementExtractor:
    def __init__(self, llm: Optional[LLMClient] = None) -> None:
        self.llm = llm or LLMClient()
    async def extract(
        self,
        message: str,
        known_categories: Optional[List[str]] = None,
        attribute_vocabulary: Optional[Dict[str, List[str]]] = None,
        current_product: Optional[Dict[str, Any]] = None,
    ) -> RequirementSummary:
       
        known_categories = known_categories or []
        context_line = ""
        if current_product:
            context_line = (
                " The user may be viewing this product right now — resolve "
                "references like 'this', 'it', 'same', 'cheaper than this' "
                "using its data: " + str({
                    "title": current_product.get("title"),
                    "category": current_product.get("category"),
                    "price": current_product.get("price"),
                    "attributes": current_product.get("attributes"),
                })
            )
        attribute_vocabulary = attribute_vocabulary or {}
        data = await self.llm.json_completion(
            system_prompt=(
                "You extract ecommerce shopping requirements. Return only JSON. "
                "Separate hard_constraints from preferences. Never invent values. "
                "Use numeric budgets and dimensions when present. Preserve "
                "merchant attribute names in hard_constraints or preferences."
            ),
            
            user_prompt=(
                "Extract this message into keys category, quantity, budget_min, "
                "budget_max, currency, use_case, hard_constraints, preferences, "
                "product_ids, and scope. scope must be \"current_product\" if the "
                "message is about the single product currently being viewed "
                "(uses words like this/it/that, or asks about its specs/price/fit), "
                "or \"catalog\" if it asks whether other/different/cheaper/alternative "
                "products exist, or browses the wider catalog. Prefer one of these "
                "catalog categories when appropriate: " + ", ".join(known_categories[:100]) +
                ". Known catalog attributes and values: " +  context_line+
                str({key: values[:30] for key, values in attribute_vocabulary.items()}) +
                ". Message: " + message
            ),
        )
        if data:
            try:
                parsed = RequirementSummary.model_validate(data)
                deterministic = self._heuristic_extract(
                    message,
                    known_categories,
                    attribute_vocabulary,
                )
                if not parsed.category:
                    parsed.category = deterministic.category
                if parsed.quantity is None:
                    parsed.quantity = deterministic.quantity
                if parsed.budget_min is None:
                    parsed.budget_min = deterministic.budget_min
                if parsed.budget_max is None:
                    parsed.budget_max = deterministic.budget_max
                if not parsed.currency:
                    parsed.currency = deterministic.currency
                if not parsed.use_case:
                    parsed.use_case = deterministic.use_case

                merged_constraints = dict(parsed.hard_constraints or {})
                merged_constraints.update(deterministic.hard_constraints)
                parsed.hard_constraints = merged_constraints

                merged_preferences = dict(parsed.preferences or {})
                merged_preferences.update(deterministic.preferences)
                parsed.preferences = merged_preferences
                return parsed
            except Exception:
                pass
        return self._heuristic_extract(message, known_categories, attribute_vocabulary)
    def _heuristic_extract(
        self,
        message: str,
        known_categories: List[str],
        attribute_vocabulary: Dict[str, List[str]],
    ) -> RequirementSummary:
        text = message.lower()
        budget_min: Optional[float] = None
        budget_max: Optional[float] = None
        currency: Optional[str] = None
        money_pattern = re.compile(
            r"(?P<prefix>under|below|less than|up to|max(?:imum)?|between|from)?\s*"
            r"(?P<currency>₹|rs\.?|inr|\$|usd)?\s*"
            r"(?P<number>\d[\d,]*(?:\.\d+)?)\s*"
            r"(?P<suffix>k|thousand|lakh)?\s*"
            r"(?P<suffix_currency>₹|rs\.?|inr|\$|usd)?",
            re.IGNORECASE,
        )
        amounts = []
        for match in money_pattern.finditer(text):
            number = self._parse_number(match.group("number"), match.group("suffix"))
            if number is None:
                continue
            raw = match.group(0)
            if not match.group("currency") and not any(
                token in raw
                for token in ("under", "below", "less", "up to", "maximum", "between", "from")
            ):
                continue
            amounts.append((match, number))
            c = (
                (match.group("currency") or "")
                + (match.group("suffix_currency") or "")
            ).lower()
            if "₹" in c or "rs" in c or "inr" in c:
                currency = "INR"
            elif "$" in c or "usd" in c:
                currency = "USD"
        if amounts:
            if len(amounts) >= 2 and "between" in text:
                budget_min, budget_max = amounts[0][1], amounts[1][1]
            else:
                budget_max = amounts[-1][1]
        quantity_match = re.search(
            r"\b(\d+)\s+(?:(?:[a-z-]+)\s+){0,3}"
            r"(?:products?|items?|chairs?|stools?|units?)\b",
            text,
        )
        quantity = int(quantity_match.group(1)) if quantity_match else None
        category = self._find_category(text, known_categories)
        use_case = self._find_use_case(text)
        hard_constraints: Dict[str, Any] = {}
        preferences: Dict[str, Any] = {}
        if budget_max is not None:
            hard_constraints["budget_max"] = budget_max
        if budget_min is not None:
            hard_constraints["budget_min"] = budget_min
        if "in stock" in text or "available" in text:
            hard_constraints["availability"] = True

        range_pattern = re.compile(
            r"(under|below|less than|up to|max(?:imum)?|"
            r"over|above|more than|min(?:imum)?)\s+"
            r"(?:([a-z]+)\s+)?(\d[\d,]*(?:\.\d+)?)\s*([a-z]+)?",
            re.IGNORECASE,
        )
        for m in range_pattern.finditer(text):
            direction = m.group(1).lower()
            unit = (m.group(2) or m.group(4) or "").strip().lower()
            number = self._parse_number(m.group(3), None)
            if number is None or not unit:
                continue
            field_match = None
            for field in attribute_vocabulary.keys():
                if unit in re.sub(r"[_-]+", " ", field.lower()):
                    field_match = self._field_name(field)
                    break
            if not field_match:
                continue
            bound = "max" if direction in (
                "under", "below", "less than", "up to", "max", "maximum"
            ) else "min"
            existing = hard_constraints.get(field_match, {})
            if not isinstance(existing, dict):
                existing = {}
            existing[bound] = number
            hard_constraints[field_match] = existing

        for field, values in attribute_vocabulary.items():
            field_label = re.sub(
                r"[_-]+",
                " ",
                str(field).lower(),
            ).strip()
            for value in values:
                value_text = str(value).strip().lower()
                if not value_text:
                    continue
                if (
                    len(value_text) == 1
                    and field_label not in text
                ):
                    continue
                if re.search(
                    rf"\b{re.escape(value_text)}\b",
                    text,
                ):
                    preferences[self._field_name(field)] = value
                    break
        if re.search(r"\b(back|backrest|back support|headrest)\b", text):
            preferences["backrest"] = True
        if any(word in text for word in ("comfortable", "comfort", "ergonomic")):
            preferences["comfort"] = "high"
        return RequirementSummary(
            category=category,
            quantity=quantity,
            budget_min=budget_min,
            budget_max=budget_max,
            currency=currency,
            use_case=use_case,
            hard_constraints=hard_constraints,
            preferences=preferences,
        )
    @classmethod
    def _canonical_category(
        cls,
        category: Optional[str],
        known_categories: List[str],
    ) -> Optional[str]:
        if not category:
            return None
        normalized_category = cls._field_name(category)
        for known_category in known_categories:
            if (
                cls._field_name(known_category)
                == normalized_category
            ):
                return known_category
        return None
    @staticmethod
    def _parse_number(number: str, suffix: Optional[str]) -> Optional[float]:
        try:
            value = float(number.replace(",", ""))
        except (TypeError, ValueError):
            return None
        suffix = (suffix or "").lower()
        if suffix in ("k", "thousand"):
            value *= 1000
        elif suffix == "lakh":
            value *= 100000
        return value
    @staticmethod
    def _field_name(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")
    @classmethod
    def _find_category(cls, text: str, known_categories: List[str]) -> Optional[str]:
        text_tokens = set(re.findall(r"[a-z0-9]+", text.lower()))
        matches = []
        for category in known_categories:
            category_tokens = set(re.findall(r"[a-z0-9]+", str(category).lower()))
            if category_tokens and category_tokens.issubset(text_tokens):
                matches.append((len(category_tokens), str(category)))
        if matches:
            return max(matches, key=lambda item: item[0])[1]
        return None
    @staticmethod
    def _find_use_case(text: str) -> Optional[str]:
        match = re.search(r"\bfor\s+(?:a|an|the)?\s*([a-z][a-z0-9 -]{2,40}?)(?=\s+(?:under|below|with|and)|$)", text)
        return match.group(1).strip() if match else None

