from typing import Any, Dict, List


from .ranking_engine import RankingEngine
from models.agent_schemas import RequirementSummary


class ComparisonEngine:
    def __init__(self, ranking: RankingEngine | None = None) -> None:
        self.ranking = ranking or RankingEngine()

    def compare(
        self,
        products: List[Dict[str, Any]],
        requirements: RequirementSummary | None = None,
    ) -> Dict[str, Any]:
        requirements = requirements or RequirementSummary()
        ranked = self.ranking.rank(products, requirements, strict=False)
        by_id = {item["id"]: item for item in ranked}
        columns = {"price": "Price", "brand": "Brand", "category": "Category", "available": "Available"}
        attribute_names = set()
        for product in products:
            attribute_names.update(product.get("attributes", {}).keys())
        for name in sorted(attribute_names):
            columns[name] = name.replace("_", " ").title()

        rows = []
        for product in products:
            row = {
                "id": product["id"],
                "title": product["title"],
                "values": {
                    "price": product.get("price"),
                    "brand": product.get("brand"),
                    "category": product.get("category"),
                    "available": product.get("available"),
                    **product.get("attributes", {}),
                },
                "score": by_id.get(product["id"], {}).get("score"),
            }
            rows.append(row)

        best_overall = max(ranked, key=lambda item: item.get("score", 0), default=None)
        available = [p for p in products if p.get("available")]
        best_value = min(available, key=lambda p: p.get("price") or float("inf"), default=None)
        return {
            "columns": columns,
            "rows": rows,
            "verdict": {
                "best_overall": best_overall.get("id") if best_overall else None,
                "best_value": best_value.get("id") if best_value else None,
            },
        }
