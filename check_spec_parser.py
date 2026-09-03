"""Standalone check for spec_parser.py - run from the repo root.

    python3 check_spec_parser.py

spec_parser imports nothing but the standard library, so this works before any
other file is touched. Every product below is from a vertical the parser has
never seen; the units must survive and no two labels may collide.
"""
from services.shopnexai.spec_parser import display_label, get_numeric, parse_specs


def rows(*pairs):
    return "<ul>" + "".join(f"<li>{k}: {v}</li>" for k, v in pairs) + "</ul>"


CASES = [
    ("jeans", "Levi's 511 Slim Fit Jeans",
     rows(("Waist", "34 in"), ("Inseam", "32 in"), ("Fabric Weight", "12 oz")),
     {"waist_in": 34.0, "inseam_in": 32.0, "fabric_weight_oz": 12.0}),
    ("supplement", "Now Foods Vitamin D3 5000 IU",
     rows(("Vitamin D3", "5000 IU"), ("Count", "120 Capsules")),
     {"vitamin_d3_iu": 5000.0, "count_capsules": 120.0, "iu": 5000.0}),
    ("phone", "Smartphone X Pro 256GB",
     rows(("Battery", "5000 mAh"), ("Storage", "256 GB"), ("Weight", "198 g")),
     {"battery_mah": 5000.0, "storage_gb": 256.0, "weight_g": 198.0, "gb": 256.0}),
    ("tyre", "Touring Tyre 205/55 R16",
     rows(("Pressure", "2.4 bar"), ("Warranty", "5 years")),
     {"pressure_bar": 2.4, "warranty_years": 5.0}),
    ("furniture", "Oak Writing Desk",
     rows(("Height", "75 cm"), ("Max Load", "40 kg")),
     {"height_cm": 75.0, "max_load_kg": 40.0}),
    ("invented unit", "Widget",
     rows(("Flux Rating", "42 zqx"), ("Peak Flux", "90 ZQX")),
     {"flux_rating_zqx": 42.0, "peak_flux_zqx": 90.0}),
    ("HVAC", "PA 24,000 BTU Mini-Split - 230V",
     rows(("Cooling Capacity (BTU)", "24,000"), ("Coverage Area (sq. ft.)", "1,000")),
     # "btu" is the headline figure from the title, "v" the digit-glued 230V.
     {"cooling_capacity_btu": 24000.0, "coverage_area_sqft": 1000.0,
      "btu": 24000.0, "v": 230.0}),
]

PROSE = [
    "<p>Sunflower oil is rich in omega 6 for a healthy coat.</p>",
    "<p>There is a reason this cabinet is popular. Any room, any style.</p>",
    "<p>Rated 4.8 by 2,000 happy customers worldwide.</p>",
]

failures = 0

for name, title, body, expected in CASES:
    actual = parse_specs(title=title, description=body)
    ok = actual == expected
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  {name:14s} {actual}")
    if not ok:
        print(f"      expected {expected}")

for body in PROSE:
    actual = parse_specs(title="Some Product", description=body)
    ok = actual == {}
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  prose rejected {actual}")

product = {"attributes": {"battery_mah": 5000.0}, "title": "Phone", "description": ""}
checks = [
    ("get_numeric exact key", get_numeric(product, "battery_mah"), 5000.0),
    ("get_numeric by unit", get_numeric(product, "mah"), 5000.0),
    ("get_numeric by label", get_numeric(product, "battery"), 5000.0),
    ("no substring bleed", get_numeric(product, "v"), None),
    ("display label", display_label({"title": "PA 24,000 BTU Mini-Split"}, "btu"), "BTU"),
]
for label, actual, expected in checks:
    ok = actual == expected
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  {label:22s} {actual!r}")

print()
print("ALL CHECKS PASSED" if not failures else f"{failures} CHECK(S) FAILED")
raise SystemExit(1 if failures else 0)
