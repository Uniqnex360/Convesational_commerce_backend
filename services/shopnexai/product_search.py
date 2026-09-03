
from typing import Any, Dict, List, Optional

from models.agent_schemas import ProductCard, ProductSearchResponse, RequirementSummary

from .product_repository import ProductRepository
from .ranking_engine import RankingEngine
from .requirement_extractor import RequirementExtractor


class ProductSearchService:
    def __init__(
        self,
        repository: Optional[ProductRepository] = None,
        ranking: Optional[RankingEngine] = None,
        extractor: Optional[RequirementExtractor] = None,
    ) -> None:
        self.repository = repository or ProductRepository()
        self.ranking = ranking or RankingEngine()
        self.extractor = extractor or RequirementExtractor()

    async def search(
        self,
        query: str = "",
        requirements: Optional[RequirementSummary] = None,
        limit: int = 10,
        strict: bool = True,
        exclude_ids: Optional[List[str]] = None,
    ) -> ProductSearchResponse:
       
        limit = max(1, min(limit, 50))
        requirements = requirements or await self._extract_requirements(query)

        candidates = self.repository.search(query=query, limit=max(100, limit * 5))
        ranked = self.ranking.rank(
            candidates,
            requirements,
            strict=strict,
            exclude_ids=exclude_ids,
        )

        exact_match = True
        if not ranked and strict:
            availability_required=(
                requirements.hard_constraints.get('availability')is True
                
            )
            if availability_required:
                return ProductSearchResponse(
                    products=[],
                    total=0,
                    exact_match=False
                )
            ranked = self.ranking.rank(
                candidates,
                requirements,
                strict=False,
                exclude_ids=exclude_ids,
            )
            exact_match = False

        products = [self._to_card(product) for product in ranked[:limit]]
        return ProductSearchResponse(
            products=products,
            total=len(products),
            exact_match=exact_match,
        )

    async def search_alternatives(
        self,
        product_id: str,
        query: str = "",
        requirements: Optional[RequirementSummary] = None,
        limit: int = 10,
    ) -> ProductSearchResponse:
        current = self.repository.get(product_id)
        if not current:
            return ProductSearchResponse(products=[], total=0, exact_match=False)

        if not query:
            query = " ".join(
                filter(
                    None,
                    [
                        current.get("title"),
                        current.get("brand"),
                        current.get("category"),
                    ],
                )
            )

        if requirements is None:
            requirements = await self._extract_requirements(query)
        # if not requirements.category:
        #     requirements.category = current.get("category")

        return await self.search(
            query=query,
            requirements=requirements,
            limit=limit,
            strict=False,
            exclude_ids=[str(product_id)],
        )

    def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        return self.repository.get(product_id)

    def get_products(self, product_ids: List[str]) -> List[Dict[str, Any]]:
        return self.repository.get_many(product_ids)

    async def _extract_requirements(self, query: str) -> RequirementSummary:
        return await self.extractor.extract(
            query,
            known_categories=self.repository.categories(),
            attribute_vocabulary=self.repository.attribute_vocabulary(),
        )

    @staticmethod
    def _to_card(product: Dict[str, Any]) -> ProductCard:
        return ProductCard(
            id=str(product.get("id", "")),
            title=product.get("title") or "Untitled product",
            price=product.get("price"),
            currency=product.get("currency"),
            brand=product.get("brand"),
            category=product.get("category"),
            image=product.get("image"),
            handle=product.get("handle"),
            product_url=product.get("product_url"),
            available=product.get("available"),
            score=product.get("score"),
            reasons=product.get("reasons", []),
            compromises=product.get("compromises", []),
            attributes=product.get("attributes", {}),
        )
