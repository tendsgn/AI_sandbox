"""
Diagnostisch script: test de KOOP SRU API stap voor stap.

Gebruik:
    python diagnose.py

Stappen:
  1. explain: geeft alle ondersteunde schema's en CQL-velden terug
  2. Kale query zonder recordSchema of TYPE_FILTER (meest basale test)
  3. Query mét geldend-filter
  4. Volledige query inclusief type-filter
"""

import sys
import textwrap
from xml.etree import ElementTree as ET

import requests

BASE_URL    = "https://zoekservice.overheid.nl/sru/Search"
CONNECTION  = "BWB"
VERSION     = "1.2"
TEST_QUERY  = 'overheid.authority = "Infrastructuur en Waterstaat"'
GELDEND     = 'overheidbwb.geldigheidsstatus = "geldend"'
TYPE_FILTER = (
    'dcterms.type = "wet" OR '
    'dcterms.type = "AMvB" OR '
    'dcterms.type = "ministeriele-regeling" OR '
    'dcterms.type = "KB"'
)


def sru_get(extra_params: dict) -> tuple[int, str, ET.Element | None]:
    base = {
        "version":      VERSION,
        "x-connection": CONNECTION,
    }
    base.update(extra_params)
    try:
        resp = requests.get(BASE_URL, params=base, timeout=30)
        try:
            root = ET.fromstring(resp.content)
        except ET.ParseError:
            root = None
        return resp.status_code, resp.text, root
    except requests.RequestException as exc:
        print(f"  VERBINDINGSFOUT: {exc}")
        sys.exit(1)


def count_records(root: ET.Element | None) -> int:
    if root is None:
        return -1
    for tag in [
        "{http://www.loc.gov/zing/srw/}numberOfRecords",
        "numberOfRecords",
    ]:
        el = root.find(".//" + tag)
        if el is not None and el.text:
            try:
                return int(el.text.strip())
            except ValueError:
                pass
    return 0


def print_section(title: str) -> None:
    print()
    print("=" * 65)
    print(f"  {title}")
    print("=" * 65)


def print_xml(text: str, chars: int = 3000) -> None:
    print(textwrap.indent(text[:chars], "  "))
    if len(text) > chars:
        print(f"  ... ({len(text) - chars} tekens weggelaten)")


# ---------------------------------------------------------------------------
# Stap 0: verbinding
# ---------------------------------------------------------------------------
print_section("Stap 0: verbindingstest")
status, raw, root = sru_get({"operation": "explain"})
print(f"  HTTP-status: {status}")
if status != 200:
    print("  Fout: server niet bereikbaar of geeft fout terug.")
    print_xml(raw)
    sys.exit(1)
print("  Verbinding OK.")

# ---------------------------------------------------------------------------
# Stap 1: explain — welke schema's en CQL-velden zijn beschikbaar?
# ---------------------------------------------------------------------------
print_section("Stap 1: explain (beschikbare schema's en velden)")
print_xml(raw)

# ---------------------------------------------------------------------------
# Stap 2: kale query — geen recordSchema, geen filters
# ---------------------------------------------------------------------------
print_section("Stap 2: kale query (geen schema, geen filters)")
params = {
    "operation":      "searchRetrieve",
    "query":          TEST_QUERY,
    "maximumRecords": 1,
}
status2, raw2, root2 = sru_get(params)
print(f"  HTTP-status:    {status2}")
print(f"  Totaal records: {count_records(root2)}")
print_xml(raw2)

# ---------------------------------------------------------------------------
# Stap 3: mét geldend-filter, géén recordSchema, géén type-filter
# ---------------------------------------------------------------------------
print_section("Stap 3: met geldend-filter (geen schema, geen type)")
params3 = {
    "operation":      "searchRetrieve",
    "query":          f"({TEST_QUERY}) AND ({GELDEND})",
    "maximumRecords": 1,
}
status3, raw3, root3 = sru_get(params3)
print(f"  HTTP-status:    {status3}")
print(f"  Totaal records: {count_records(root3)}")
print_xml(raw3)

# ---------------------------------------------------------------------------
# Stap 4: mét geldend-filter én type-filter, géén recordSchema
# ---------------------------------------------------------------------------
print_section("Stap 4: met geldend + type-filter (geen schema)")
params4 = {
    "operation":      "searchRetrieve",
    "query":          f"({TEST_QUERY}) AND ({GELDEND}) AND ({TYPE_FILTER})",
    "maximumRecords": 1,
}
status4, raw4, root4 = sru_get(params4)
print(f"  HTTP-status:    {status4}")
print(f"  Totaal records: {count_records(root4)}")
print_xml(raw4)

# ---------------------------------------------------------------------------
# Stap 5: zelfde als stap 4 maar MÉT recordSchema=gzd
# ---------------------------------------------------------------------------
print_section("Stap 5: zelfde als stap 4 + recordSchema=gzd")
params5 = {
    "operation":      "searchRetrieve",
    "query":          f"({TEST_QUERY}) AND ({GELDEND}) AND ({TYPE_FILTER})",
    "maximumRecords": 1,
    "recordSchema":   "gzd",
}
status5, raw5, root5 = sru_get(params5)
print(f"  HTTP-status:    {status5}")
print(f"  Totaal records: {count_records(root5)}")
print_xml(raw5)

print()
print("=" * 65)
print("  Diagnose klaar. Zie bovenstaande XML voor correcte")
print("  namespace-paden, schema-namen en veldwaarden.")
print("=" * 65)
