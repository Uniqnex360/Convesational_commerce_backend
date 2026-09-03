import re
from typing import Any, Dict, Iterable, List, Optional
from models.schemas import ShopifyProduct
import os
class ProductRepository:
    def categories(self, limit: int = 500) -> List[str]:
        try:
            documents = list(
                ShopifyProduct.objects.limit(limit)
            )
        except Exception:
            return []
        values = set()
        for document in documents:
            product = self.normalize(document)
            if product.get("category"):
                values.add(str(product["category"]))
        return sorted(values)
    _SEARCH_STOPWORDS = {
        "a",
        "an",
        "and",
        "are",
        "available",
        "availability",
        "below",
        "find",
        "for",
        "in",
        "is",
        "item",
        "items",
        "less",
        "me",
        "my",
        "of",
        "please",
        "product",
        "products",
        "show",
        "than",
        "the",
        "to",
        "under",
        "up",
        "with",
    }
    def attribute_vocabulary(
        self,
        limit: int = 500,
    ) -> Dict[str, List[str]]:
        try:
            documents = list(
                ShopifyProduct.objects.limit(limit)
            )
        except Exception:
            return {}
        vocabulary: Dict[str, set[str]] = {}
        for document in documents:
            product = self.normalize(document)
            for name, value in product.get(
                "attributes",
                {},
            ).items():
                values = value if isinstance(value, list) else [value]
                for item in values:
                    if item not in (None, "", [], {}):
                        vocabulary.setdefault(
                            str(name),
                            set(),
                        ).add(str(item))
        return {
            name: sorted(values)
            for name, values in vocabulary.items()
        }
    def search(
        self,
        query: str = "",
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        try:
            documents = list(
                ShopifyProduct.objects.limit(
                    max(limit, 1) * 5
                )
            )
        except Exception:
            return []

        products = [
            self.normalize(document)
            for document in documents
        ]

        query_tokens = self._tokens(query)

        meaningful_tokens = [
            token
            for token in query_tokens
            if token not in self._SEARCH_STOPWORDS
            and not token.isdigit()
            and token not in {
                "usd",
                "inr",
                "rs",
            }
        ]

        # A generic request such as "show available products"
        # has no product-specific search terms. In that case,
        # return all candidates and let RankingEngine apply
        # budget and availability requirements.
        if not meaningful_tokens:
            return products[:limit]

        scored = []

        for product in products:
            searchable = " ".join(
                [
                    str(product.get("title") or ""),
                    str(product.get("brand") or ""),
                    str(product.get("category") or ""),
                    str(product.get("description") or ""),
                    " ".join(
                        str(value)
                        for value in product.get(
                            "attributes",
                            {},
                        ).values()
                    ),
                ]
            )

            # Match complete tokens, not substrings.
            searchable_tokens = set(
                self._tokens(searchable)
            )

            matched_tokens = [
                token
                for token in meaningful_tokens
                if token in searchable_tokens
            ]

            if not matched_tokens:
                continue

            token_score = len(matched_tokens)

            # Give a small bonus when the complete query phrase
            # occurs in the product text.
            normalized_query = " ".join(
                meaningful_tokens
            ).lower()

            normalized_searchable = searchable.lower()

            if normalized_query in normalized_searchable:
                token_score += 2

            scored.append((token_score, product))

        scored.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        return [
            product
            for _, product in scored[:limit]
        ]
    def get(
        self,
        product_id: str,
    ) -> Optional[Dict[str, Any]]:
        try:
            numeric_id = int(
                str(product_id).split("/")[-1]
            )
            document = ShopifyProduct.objects.get(
                _id=numeric_id
            )
            return self.normalize(document)
        except Exception:
            return None
    def get_many(
        self,
        product_ids: Iterable[str],
    ) -> List[Dict[str, Any]]:
        products = []
        for product_id in product_ids:
            product = self.get(str(product_id))
            if product:
                products.append(product)
        return products
    def normalize(
        self,
        document: Any,
    ) -> Dict[str, Any]:
        def get_value(
            name: str,
            default: Any = None,
        ) -> Any:
            if isinstance(document, dict):
                return document.get(name, default)
            return getattr(
                document,
                name,
                default,
            )
        variants = get_value("variants", []) or []
        first_variant = (
            variants[0]
            if variants
            else {}
        )
        if not isinstance(first_variant, dict):
            first_variant = {}
        price = self._number(
            first_variant.get("price")
        )
        if price is None:
            price = self._number(
                get_value("price")
            )
        attributes: Dict[str, Any] = {}
        raw_attributes = (
            get_value("attributes", {})
            or {}
        )
        if isinstance(raw_attributes, dict):
            attributes.update(raw_attributes)
        specifications = (
            get_value("specifications", {})
            or {}
        )
        if isinstance(specifications, dict):
            attributes.update(specifications)
        raw_document = (
            document
            if isinstance(document, dict)
            else getattr(document, "_data", {})
        )
        ignored_fields = {
            "_id",
            "id",
            "title",
            "product_name",
            "name",
            "body_html",
            "description",
            "long_description",
            "price",
            "currency",
            "vendor",
            "brand",
            "brand_name",
            "product_type",
            "category",
            "category_id",
            "category_1",
            "category_2",
            "category_3",
            "category_4",
            "category_5",
            "status",
            "handle",
            "tags",
            "image",
            "image_url",
            "images",
            "variants",
            "sku",
            "inStock",
            "available",
            "attributes",
            "specifications",
            "created_at",
            "updated_at",
            "last_synced",
            "shopify_updated_at",
        }
        if isinstance(raw_document, dict):
            for field, value in raw_document.items():
                if (
                    field not in ignored_fields
                    and value not in (None, "", [], {})
                ):
                    attributes[field] = value
        inventory_values = [
            variant.get("inventory_quantity")
            for variant in variants
            if (
                isinstance(variant, dict)
                and "inventory_quantity" in variant
            )
        ]
        if inventory_values:
            available = any(
                (self._number(value) or 0) > 0
                for value in inventory_values
            )
        else:
            available = get_value(
                "status",
                "active",
            ) not in (
                "draft",
                "archived",
                "inactive",
            )
        if get_value("available") is not None:
            available = bool(
                get_value("available")
            )
        product_id = get_value(
            "_id",
            get_value(
                "id",
                get_value(
                    "productId",
                    get_value(
                        "product_id",
                        "",
                    ),
                ),
            ),
        )
        storefront_url = (
            os.getenv("SHOPNEXAI_STOREFRONT_URL") or ""
        ).rstrip("/")
        handle = get_value("handle")
        product_url = (
            get_value("product_url")
            or get_value("url")
        )
        if (
            not product_url
            and storefront_url
            and handle
        ):
            product_url = (
                f"{storefront_url}/products/{handle}"
            )
        return {
            "id": str(product_id),
            "title": (
                get_value("title")
                or get_value("product_name")
                or get_value("name")
                or "Untitled product"
            ),
            "description": (
                get_value("body_html")
                or get_value("description")
                or get_value("long_description")
                or ""
            ),
            "price": price,
            "currency": (
                get_value("currency")
                or "USD"
            ),
            "brand": (
                get_value("brand")
                or get_value("vendor")
                or get_value("brand_name")
            ),
            "image": (
                get_value("image_url")
                or get_value("image")
            ),
            "handle": handle,
            "product_url": product_url,
            "category": (
                get_value("product_type")
                or get_value("category")
                or get_value("category_5")
                or get_value("category_4")
            ),
            "available": (
                get_value("inStock")
                if get_value("inStock") is not None
                else available
            ),
            "sku": (
                get_value("sku")
                or first_variant.get("sku")
            ),
            "image": (
                get_value("image_url")
                or get_value("image")
            ),
            "handle": get_value("handle"),
            "attributes": attributes,
            "variants": variants,
        }
    @staticmethod
    def _tokens(value: str) -> List[str]:
        return [
            token
            for token in re.findall(
                r"[a-z0-9]+",
                (value or "").lower(),
            )
            if len(token) > 1
        ]
    @staticmethod
    def _number(value: Any) -> Optional[float]:
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
