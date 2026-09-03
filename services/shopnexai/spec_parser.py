"""Derive structured numeric attributes from unstructured product text.

Why this exists
---------------
``ShopifyProduct.attributes`` is empty for most synced products, so numeric
questions ("anything below 24,000 BTU?", "covers 400 sq ft?") had no data to
filter on. The values live in the title and in the spec rows inside
``body_html`` (``Cooling Capacity (BTU): 24,000``).

Design constraints
------------------
This is a multi-tenant SDK: the next merchant may sell clothing, supplements or
tyres. So nothing here knows what a unit *is* by name. Instead:

* **Structure over vocabulary.** Spec rows are extracted from list/table
  elements (``li``, ``td``, ``th``, ``dt``, ``dd``). Prose lives in ``p`` and is
  never a candidate, which removes any need for a hardcoded "these words mean
  this is a sentence" blocklist.
* **The merchant's own words become the attribute name.** ``Waist: 34 in``
  yields ``waist_in``. Labels are never replaced by units, so two different
  measurements sharing a unit cannot collide.
* **The unit is preserved in the key.** Grams and gsm never collapse into one
  ``weight`` attribute that ranking would happily compare across products.
* **A short built-in spelling map only normalizes punctuation and spacing**
  (``sq. ft.`` -> ``sqft``). It never decides that two different words mean the
  same thing. Merchants can extend it via ``SHOPNEXAI_UNIT_ALIASES_JSON``.
"""

import json
import os
import re
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

# Spelling normalization only: mechanical slug + optional merchant-supplied
# aliases. Deliberately does NOT map "square feet" onto "sqft" - guessing that
# two different phrases mean the same unit is exactly the kind of hardcoded
# product knowledge this module must not contain.
def _load_unit_aliases() -> Dict[str, str]:
    raw = os.getenv("SHOPNEXAI_UNIT_ALIASES_JSON")
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return {}
    aliases: Dict[str, str] = {}
    if isinstance(data, dict):
        # {"sqft": ["sq ft", "square feet"]} -> both spellings map to "sqft"
        for canonical, spellings in data.items():
            target = _slug_unit(str(canonical))
            if not target:
                continue
            if isinstance(spellings, str):
                spellings = [spellings]
            if isinstance(spellings, Iterable):
                aliases[target] = target
                for spelling in spellings:
                    slug = _slug_unit(str(spelling))
                    if slug:
                        aliases[slug] = target
    return aliases


_BLOCK_TAG = re.compile(
    r"(?i)</?(?:p|div|li|ul|ol|tr|td|th|table|thead|tbody|br|h[1-6]|section|"
    r"article|dl|dt|dd|figure|blockquote)\b[^>]*>"
)
_ANY_TAG = re.compile(r"<[^>]+>")

# Elements whose contents are spec rows rather than marketing prose.
_ROW_TAG = re.compile(r"(?i)<(li|td|th|dt|dd)\b[^>]*>(.*?)</\1>", re.DOTALL)

_NUMBER = r"\d[\d,]*(?:\.\d+)?"
_SIGNED_NUMBER = rf"-?{_NUMBER}"

# A unit token written next to a number in free text ("24,000 BTU", "180cm").
# Length-capped so that ordinary nouns are not mistaken for units:
#   "180cm" -> cm (2)      "24,000 BTU" -> btu (3)     "5000 mAh" -> mah (3)
#   "2024 Model" -> rejected (5)   "6 Bottles" -> rejected (7)
_MAX_INLINE_UNIT_LEN = 4

# Labels are rejected when they look like a sentence rather than a spec name.
_MAX_LABEL_WORDS = 5
_MAX_LABEL_CHARS = 40

# Written as escapes so this source file stays pure ASCII: a terminal or
# clipboard that cannot represent these code points silently replaces them,
# which corrupts the character classes below without raising any error.
_MIDDLE_DOT = "\u00b7"
_BULLET = "\u2022"
_SUPER_TWO = "\u00b2"
_DEGREE = "\u00b0"

# "12.5 x 12.5 x 14" is a dimension chain: the letters separate numbers, they
# are not units. Detected structurally (number, then two or more
# letter-plus-number repeats) so no separator character has to be named here.
_DIMENSION_CHAIN = re.compile(
    rf"(?<![A-Za-z0-9]){_NUMBER}(?:\s*[A-Za-z]\s*{_NUMBER}){{2,}}",
    re.IGNORECASE,
)


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------

def _slug_unit(value: str) -> str:
    """Mechanical unit slug: lowercase, drop punctuation and spaces."""
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def _slug_label(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").lower()).strip("_")


def _to_number(raw: str) -> Optional[float]:
    try:
        return float(str(raw).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _coerce(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, list):
        for item in value:
            coerced = _coerce(item)
            if coerced is not None:
                return coerced
        return None
    if isinstance(value, str):
        match = re.search(_NUMBER, value.replace(",", ""))
        if match:
            return _to_number(match.group(0))
    return None


def _plain(text: str) -> str:
    return re.sub(r"\s+", " ", _ANY_TAG.sub(" ", text or "")).strip()


# --------------------------------------------------------------------------
# Row extraction (structure, not vocabulary)
# --------------------------------------------------------------------------

def _spec_rows(description: str) -> List[str]:
    """Return candidate spec rows from list/table markup.

    Falls back to newline-separated lines when the merchant stored plain text
    instead of HTML, so a catalog without markup still gets parsed.
    """
    text = description or ""
    if not text.strip():
        return []

    rows: List[str] = []
    for match in _ROW_TAG.finditer(text):
        inner = _plain(match.group(2))
        if inner:
            rows.append(inner)

    if rows:
        return rows

    if "<" not in text:
        return [line.strip() for line in text.splitlines() if line.strip()]

    # Markup exists but has no list/table rows: split on block tags. Prose
    # paragraphs are still included here, but only a "Label: number" shaped
    # segment can match below, which is a structural test rather than a
    # vocabulary one.
    spaced = _BLOCK_TAG.sub("\n", text)
    return [
        re.sub(r"\s+", " ", line).strip()
        for line in _ANY_TAG.sub(" ", spaced).split("\n")
        if line.strip()
    ]


def _looks_like_label(label: str) -> bool:
    """Structural test for 'this is a spec name', with no word list."""
    words = label.split()
    if not words or len(words) > _MAX_LABEL_WORDS:
        return False
    if len(label) > _MAX_LABEL_CHARS:
        return False
    # Must start with a letter and contain no sentence punctuation.
    if not words[0][:1].isalpha():
        return False
    if any(char in label for char in ".!?;,"):
        return False
    return True


# --------------------------------------------------------------------------
# Parsers
# --------------------------------------------------------------------------

def _split_segments(line: str) -> List[str]:
    separators = "[|" + _MIDDLE_DOT + _BULLET + "]"
    return [
        s.strip()
        for s in re.split(separators + r"|\s{2,}", line)
        if s.strip()
    ]


def _from_label_pairs(
    rows: Iterable[str],
    known_units: Optional[Set[str]] = None,
) -> Dict[str, float]:
    """Parse ``Label (unit): value`` and ``Label: value unit`` rows."""
    aliases = _load_unit_aliases()
    known_units = known_units or set()
    found: Dict[str, float] = {}
    pattern = re.compile(
        rf"^(?P<label>[A-Za-z][A-Za-z0-9 /\-&]{{1,{_MAX_LABEL_CHARS}}}?)"
        rf"(?:\s*\((?P<paren_unit>[^()]{{1,16}})\))?"
        rf"\s*[:\-]\s*(?P<number>{_SIGNED_NUMBER})"
        rf"\s*(?P<trailing_unit>[A-Za-z/%{_SUPER_TWO}{_DEGREE}.]{{0,12}})"
        rf"(?P<trailing_unit2>(?:[.\s]+[A-Za-z]{{1,10}})?)"
    )

    for row in rows:
        for segment in _split_segments(row):
            match = pattern.match(segment)
            if not match:
                continue

            raw_label = match.group("label").strip()
            if not _looks_like_label(raw_label):
                continue

            number = _to_number(match.group("number"))
            if number is None:
                continue

            paren_unit = match.group("paren_unit")
            first_word = match.group("trailing_unit") or ""
            second_word = match.group("trailing_unit2") or ""
            if paren_unit:
                unit = _slug_unit(paren_unit)
            else:
                # "Area: 80 square feet" spans two words, but so does
                # "Minimum: 2,400 BtuH. Rated 24,000 BTU". Join the pair only
                # when the merchant's own vocabulary or alias map evidences it.
                joined = aliases.get(
                    _slug_unit(first_word + second_word),
                    _slug_unit(first_word + second_word),
                )
                if (
                    second_word
                    and joined
                    and (joined in known_units or joined in aliases.values())
                ):
                    unit = joined
                else:
                    unit = _slug_unit(first_word)
            unit = aliases.get(unit, unit)

            label = _slug_label(raw_label)
            if not label:
                continue

            # Keep both the label and the unit. Replacing the label with the
            # unit is what made "Waist: 34 in" and "Inseam: 32 in" collide.
            key = f"{label}_{unit}" if unit and not label.endswith(unit) else label
            found.setdefault(key, number)

    return found


def _from_inline_units(
    text: str,
    known_units: Optional[Set[str]] = None,
    relaxed: bool = False,
) -> Dict[str, float]:
    """Parse ``24,000 BTU`` / ``180cm`` mentions where no label exists.

    A token is accepted as a unit only when it is *evidenced*, never because it
    looks like one:

    * it appears in ``known_units`` - the vocabulary learned from this catalog's
      own spec rows, so a tyre store contributes "bar" and a clothing store
      contributes "gsm" without either being named in source; or
    * it is glued to the number (``180cm``, ``256GB``, ``2000W``) and short.

    Space-separated tokens that are not in the vocabulary are rejected, which is
    what keeps "rich in omega 6 for a healthy coat" from producing ``for: 6``.
    """
    known_units = known_units or set()
    aliases = _load_unit_aliases()
    found: Dict[str, float] = {}

    pattern = re.compile(
        # A letter or digit immediately before the number means this is part of
        # a model code ("R454B"), not a measurement.
        rf"(?<![A-Za-z0-9])(?P<number>{_NUMBER})(?P<gap>\s*)(?P<unit>[A-Za-z]+)\b"
    )
    raw_text = text or ""
    lowered = raw_text.lower()
    # Case is only inspectable when lowercasing preserved the offsets.
    case_usable = len(raw_text) == len(lowered)
    chain_spans = [
        (m.start(), m.end()) for m in _DIMENSION_CHAIN.finditer(lowered)
    ]
    for match in pattern.finditer(lowered):
        number = _to_number(match.group("number"))
        if number is None:
            continue

        # "SEER2: 22.5 HSPF2" - the number belongs to the preceding label.
        # A trailing hyphen is NOT skipped: "15A-115V" carries two measurements.
        prefix = lowered[: match.start()].rstrip()
        if prefix.endswith(":"):
            continue

        unit = _slug_unit(match.group("unit"))
        unit = aliases.get(unit, unit)
        if not unit:
            continue
        if any(start <= match.start("unit") < end for start, end in chain_spans):
            continue

        adjacent = match.group("gap") == ""
        # Titles are merchant-structured ("PA 24,000 BTU Mini-Split"), so an
        # acronym written in capitals is accepted there. Body prose is not:
        # relaxing this globally let "omega 6 for a healthy coat" yield
        # {"for": 6}, and "Levi's 511 Slim Fit" would yield {"slim": 511}.
        short = len(unit) <= _MAX_INLINE_UNIT_LEN
        acronym = bool(
            relaxed
            and short
            and case_usable
            and raw_text[match.start("unit"): match.end("unit")].isupper()
        )
        if unit not in known_units and not (adjacent or acronym):
            continue

        # Highest value wins so a "minimum heating 2,400 BTU" row cannot
        # override the 24,000 BTU headline rating.
        previous = found.get(unit)
        if previous is None or number > previous:
            found[unit] = number

    return found


def discover_units(description: str) -> Set[str]:
    """Unit tokens this product's own spec rows use.

    Derived from the keys the label-pair parser actually produces, so the
    vocabulary can never drift from what parsing yields. A loose regex here is
    what turned "Coverage Area (sq. ft.): 450" into a bogus unit "sq", which
    then let prose such as "up to 450 sq. ft." create an attribute.

    Called across a catalog this yields the merchant's real unit vocabulary,
    with no hardcoded list: a tyre store discovers "bar" and "kg", a clothing
    store discovers "in" and "gsm".
    """
    units: Set[str] = set()
    for key in _from_label_pairs(_spec_rows(description)):
        slug = _slug_label(key)
        # Only a "label_unit" key contributes a unit. A single-segment key such
        # as "dimensions" or "model" is a unitless label, and treating it as a
        # unit is what let prose numbers become attributes.
        if "_" in slug:
            units.add(slug.rsplit("_", 1)[-1])
    return {unit for unit in units if unit}


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------

def parse_specs(
    title: str = "",
    description: str = "",
    known_units: Optional[Set[str]] = None,
) -> Dict[str, float]:
    """Return numeric attributes derived from a product's title and body text.

    The title is applied last so its headline capacity ("PA 24,000 BTU ...")
    wins over a secondary figure in the body.
    """
    if known_units is None:
        known_units = discover_units(description)

    rows = _spec_rows(description)

    specs: Dict[str, float] = {}
    labelled = _from_label_pairs(rows, known_units)
    specs.update(labelled)
    # Rows and title only. Running this over the whole description let prose
    # such as "omega 6 for a healthy coat" contribute a bogus attribute.
    for row in rows:
        for key, value in _from_inline_units(row, known_units).items():
            # "Vitamin D3: 5000 IU" already produced vitamin_d3_iu; a second
            # bare "iu" key is the same measurement stripped of its label.
            if "_" not in key and any(
                name.endswith(f"_{key}") and labelled[name] == value
                for name in labelled
            ):
                continue
            specs.setdefault(key, value)
    # The title is the one place a bare unit key is wanted: it is the handle a
    # shopper actually types ("any other products with btu below this").
    specs.update(_from_inline_units(_plain(title), known_units, relaxed=True))

    return {key: value for key, value in specs.items() if value is not None}


def unit_of(product: Dict[str, Any], attribute: str) -> Optional[str]:
    """The unit embedded in an attribute key, if any.

    Lets ranking refuse to compare 198 g against 240 gsm instead of silently
    treating them as the same measurable quantity.
    """
    attributes = product.get("attributes") or {}
    slug = _slug_label(attribute)
    for name in attributes:
        if _slug_label(name) == slug and "_" in slug:
            return slug.rsplit("_", 1)[-1]
    return None


def find_attributes(product: Dict[str, Any], token: str) -> List[str]:
    """Attribute keys on this product whose name contains ``token``.

    This is how a query resolves to a merchant's own attribute naming without
    a hardcoded vocabulary: "btu" finds ``cooling_capacity_btu`` and ``btu``.
    """
    needle = _slug_unit(token)
    if not needle:
        return []
    keys = []
    for name in (product.get("attributes") or {}):
        slug = _slug_label(name)
        if needle == slug or needle in slug.replace("_", ""):
            keys.append(name)
    return sorted(keys, key=len)


def get_numeric(product: Dict[str, Any], key: str) -> Optional[float]:
    """Read a numeric attribute, tolerating strings and partial key names."""
    attributes = product.get("attributes") or {}
    normalized_key = _slug_unit(key)

    exact: List[Any] = []
    partial: List[Any] = []
    for name, value in attributes.items():
        cleaned = _slug_unit(name)
        segments = [part for part in _slug_label(name).split("_") if part]
        if cleaned == normalized_key:
            exact.append(value)
        elif normalized_key and normalized_key in segments:
            # Segment-wise, not substring: a substring test lets the unit "v"
            # match "coverage_area_sqft" and return a square-footage figure.
            partial.append(value)

    for candidate in exact or partial:
        number = _coerce(candidate)
        if number is not None:
            return number

    # Fall back to the title, which merchants keep authoritative.
    for name, value in parse_specs(title=str(product.get("title") or "")).items():
        if _slug_unit(name) == normalized_key:
            return float(value)

    if normalized_key in product:
        return _coerce(product[normalized_key])

    return None


_WORD_TOKEN = re.compile(r"(?<![A-Za-z0-9])[A-Za-z0-9]{1,10}(?![A-Za-z0-9])")


def display_label(product: Dict[str, Any], attribute: str) -> str:
    """Human label for an attribute key, spelled the way the merchant spells it.

    ``btu`` renders as "BTU" because the product's own text says "BTU"; an
    attribute the parser invented from "Coverage Area (sq. ft.)" renders as
    "Coverage Area Sqft". No display name is stored in source, so a tyre store
    gets "Pressure Bar" and a supplement store gets "Vitamin D3 Iu" without
    anyone editing this file.
    """
    words = [word for word in _slug_label(attribute).split("_") if word]
    if not words:
        return "Value"
    haystack = _plain(
        " ".join(
            str(product.get(field) or "")
            for field in ("title", "description", "name")
        )
    )
    casings: Dict[str, str] = {}
    for match in _WORD_TOKEN.finditer(haystack):
        token = match.group(0)
        slug = _slug_unit(token)
        if not slug:
            continue
        # An all-caps acronym the merchant wrote is the strongest evidence.
        if slug not in casings or (token.isupper() and len(token) > 1):
            casings[slug] = token
    return " ".join(
        casings.get(word) or word.capitalize() for word in words
    )
