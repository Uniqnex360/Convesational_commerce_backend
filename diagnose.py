import hashlib, re, sys
from services.shopnexai import spec_parser as sp

path = sp.__file__
raw = open(path, "rb").read()
print("python   :", sys.version.split()[0])
print("path     :", path)
print("lines    :", raw.count(b"\n") + 1)
print("bytes    :", len(raw))
print("md5      :", hashlib.md5(raw).hexdigest())
print("EXPECTED md5: 690f00571f43eab05a3e9aef3dca26d7  (503 lines, 19014 bytes)")
print()
print("_ROW_TAG   :", repr(sp._ROW_TAG.pattern))
print("  EXPECTED : '(?i)<(li|td|th|dt|dd)\\\\b[^>]*>(.*?)</\\\\1>'")
print("_ANY_TAG   :", repr(sp._ANY_TAG.pattern))
print("_NUMBER    :", repr(sp._NUMBER))
print("  EXPECTED : '\\\\d[\\\\d,]*(?:\\\\.\\\\d+)?'")
print("MAX_LABEL_CHARS :", sp._MAX_LABEL_CHARS)
print("MAX_INLINE_UNIT :", sp._MAX_INLINE_UNIT_LEN)
print()
html = "<ul><li>Waist: 34 in</li><li>Inseam: 32 in</li></ul>"
rows = sp._spec_rows(html)
print("_spec_rows      :", rows)
print("  EXPECTED      : ['Waist: 34 in', 'Inseam: 32 in']")
print("_looks_like_label('Waist'):", sp._looks_like_label("Waist"))
print("_from_label_pairs:", sp._from_label_pairs(rows))
print("parse_specs      :", sp.parse_specs(title="Jeans", description=html))