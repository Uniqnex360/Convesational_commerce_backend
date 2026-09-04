import asyncio, json
from services.shopnexai.product_repository import ProductRepository
from services.shopnexai.requirement_extractor import RequirementExtractor
from services.shopnexai.spec_parser import parse_specs

repo = ProductRepository()
vocab = repo.attribute_vocabulary()
print("attribute_vocabulary() keys :", len(vocab))
print("  contains a btu key        :", [k for k in vocab if "btu" in k.lower()][:5])

anchor = repo.get("10118208684216")
print("anchor found                :", bool(anchor))
if anchor:
    print("anchor attribute keys       :", list((anchor.get("attributes") or {}))[:8])

ex = RequirementExtractor()
r = asyncio.run(ex.extract(
    "any products below 10000 BTU",
    known_categories=repo.categories(),
    attribute_vocabulary=vocab,
    anchor_product=anchor,
))
print("\n--- deterministic result ---")
print("budget_max      :", r.budget_max)
print("hard_constraints:", json.dumps(r.hard_constraints, default=str))
print("\nEXPECTED: budget_max=None, hard_constraints has relation=lt value=10000")
