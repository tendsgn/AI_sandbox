"""
Zoekmodule: bevraagt de KOOP SRU API voor het Basis Wettenbestand (BWB).

Eindpunt:  https://zoekservice.overheid.nl/sru/Search
Protocol:  SRU 1.2
Collectie: BWB (Basis Wettenbestand)
Formaat:   XML (SRW/SRU response, recordschema: gzd)

Beperkingen:
  - Zoekt ALLEEN op metadata, niet op wettekst.
  - Maximaal 50 records per request.
  - Alle velden zijn CQL (Contextual Query Language).

Bruikbare CQL-velden (BWB):
  overheid.authority          Verantwoordelijk ministerie
  overheidbwb.geldigheidsstatus  'geldend' / 'niet-geldend'
  dcterms.type                wet / AMvB / ministeriele-regeling / KB
  dcterms.title               Titel (gedeeltelijk)
  keyword                     Metadata-trefwoorden
  dcterms.identifier          BWB-identifier (exact)
"""

import time
import logging
from typing import Iterator
from xml.etree import ElementTree as ET

import requests

from src.config import (
    SRU_BASE_URL,
    SRU_VERSION,
    SRU_CONNECTION,
    SRU_MAX_RECORDS,
    REQUEST_DELAY_SEC,
    GELDEND_FILTER,
    TYPE_FILTER,
)

logger = logging.getLogger(__name__)

# Namespaces die voorkomen in SRU/GZD-responses van zoekservice.overheid.nl
# We proberen meerdere varianten omdat de exacte namespace kan variëren.
NS_CANDIDATES = [
    {   # Meest voorkomend voor KOOP SRU
        "srw":          "http://www.loc.gov/zing/srw/",
        "dcterms":      "http://purl.org/dc/terms/",
        "overheidbwb":  "http://standaarden.overheid.nl/bwb/",
        "overheid":     "http://standaarden.overheid.nl/owms/terms/",
        "gzd":          "http://www.gzd.nl/",
    },
    {   # Alternatieve variant
        "srw":          "http://www.loc.gov/zing/srw/",
        "dcterms":      "http://purl.org/dc/terms/",
        "overheidbwb":  "http://standaarden.overheid.nl/bwb/",
    },
]

# Velden om uit elk record te extraheren, met mogelijke namespace-varianten
FIELD_XPATHS = {
    "bwb_id": [
        ".//dcterms:identifier",
        ".//{http://purl.org/dc/terms/}identifier",
        ".//{http://www.gzd.nl/}identifier",
    ],
    "titel": [
        ".//dcterms:title",
        ".//{http://purl.org/dc/terms/}title",
        ".//{http://www.gzd.nl/}title",
    ],
    "citeertitel": [
        ".//dcterms:alternative",
        ".//{http://purl.org/dc/terms/}alternative",
    ],
    "soort_regeling": [
        ".//dcterms:type",
        ".//{http://purl.org/dc/terms/}type",
    ],
    "datum_inwerkingtreding": [
        ".//overheidbwb:datumInwerkingtreding",
        ".//{http://standaarden.overheid.nl/bwb/}datumInwerkingtreding",
    ],
    "status": [
        ".//overheidbwb:geldigheidsstatus",
        ".//{http://standaarden.overheid.nl/bwb/}geldigheidsstatus",
    ],
    "wetgever": [
        ".//dcterms:creator",
        ".//{http://purl.org/dc/terms/}creator",
        ".//dcterms:publisher",
        ".//{http://purl.org/dc/terms/}publisher",
    ],
}


# ---------------------------------------------------------------------------
# Publieke interface
# ---------------------------------------------------------------------------

def search(cql_condition: str, label: str) -> Iterator[dict]:
    """
    Voer een CQL-zoekopdracht uit op het BWB en yield records.

    cql_condition: het specifieke zoekcriterium zonder geldend-filter,
                   bijv. 'overheid.authority = "Infrastructuur en Waterstaat"'
    label:         beschrijving voor logging en output-kolom
    """
    # Combineer altijd met geldend-filter én type-filter
    full_query = (
        f"({cql_condition})"
        f" AND ({GELDEND_FILTER})"
        f" AND ({TYPE_FILTER})"
    )
    yield from _paginate(full_query, label=label)


# ---------------------------------------------------------------------------
# Interne helpers
# ---------------------------------------------------------------------------

def _paginate(cql_query: str, label: str) -> Iterator[dict]:
    """Voer een volledige query uit, inclusief automatische paginering."""
    logger.info("Zoeken: %s", label)
    try:
        root = _request(cql_query, start_record=1)
    except requests.RequestException as exc:
        logger.error("Request mislukt voor '%s': %s", label, exc)
        return

    total = _get_total(root)
    logger.info("  -> %d resultaten", total)
    if total == 0:
        return

    for rec in _get_records(root):
        parsed = _parse(rec, label)
        if parsed:
            yield parsed

    start = SRU_MAX_RECORDS + 1
    while start <= total:
        time.sleep(REQUEST_DELAY_SEC)
        try:
            root = _request(cql_query, start_record=start)
        except requests.RequestException as exc:
            logger.error("Paginering mislukt (start=%d, '%s'): %s", start, label, exc)
            break
        for rec in _get_records(root):
            parsed = _parse(rec, label)
            if parsed:
                yield parsed
        start += SRU_MAX_RECORDS


def _request(cql_query: str, start_record: int = 1) -> ET.Element:
    params = {
        "operation":      "searchRetrieve",
        "version":        SRU_VERSION,
        "x-connection":   SRU_CONNECTION,
        "query":          cql_query,
        "startRecord":    start_record,
        "maximumRecords": SRU_MAX_RECORDS,
        "recordSchema":   "gzd",
    }
    resp = requests.get(SRU_BASE_URL, params=params, timeout=30)
    resp.raise_for_status()
    return ET.fromstring(resp.content)


def _get_total(root: ET.Element) -> int:
    """Lees numberOfRecords uit de SRU-response."""
    # Probeer met en zonder namespace
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


def _get_records(root: ET.Element) -> list[ET.Element]:
    """Geef alle record-elementen in de response."""
    for tag in [
        "{http://www.loc.gov/zing/srw/}record",
        "record",
    ]:
        records = root.findall(".//" + tag)
        if records:
            return records
    return []


def _find_text(element: ET.Element, xpaths: list[str]) -> str:
    """Probeer meerdere XPath-varianten tot een waarde gevonden is."""
    for xpath in xpaths:
        try:
            el = element.find(xpath)
            if el is not None and el.text:
                return el.text.strip()
        except Exception:
            continue
    return ""


def _parse(record: ET.Element, label: str) -> dict | None:
    """Extraheer metadata uit één SRU-record."""
    try:
        # Zoek de recordData (met of zonder namespace)
        data = None
        for tag in [
            "{http://www.loc.gov/zing/srw/}recordData",
            "recordData",
        ]:
            data = record.find(".//" + tag)
            if data is not None:
                break

        if data is None:
            # Gebruik het record zelf als fallback
            data = record

        bwb_id          = _find_text(data, FIELD_XPATHS["bwb_id"])
        titel           = _find_text(data, FIELD_XPATHS["titel"])
        citeertitel     = _find_text(data, FIELD_XPATHS["citeertitel"])
        soort_regeling  = _find_text(data, FIELD_XPATHS["soort_regeling"])
        datum_iwtrd     = _find_text(data, FIELD_XPATHS["datum_inwerkingtreding"])
        status          = _find_text(data, FIELD_XPATHS["status"])
        wetgever        = _find_text(data, FIELD_XPATHS["wetgever"])

        # BWB-URL
        url = f"https://wetten.overheid.nl/{bwb_id}" if bwb_id else ""

        # Sla records zonder titel én zonder ID over
        if not titel and not bwb_id:
            return None

        return {
            "bwb_id":                 bwb_id,
            "titel":                  titel,
            "citeertitel":            citeertitel,
            "soort_regeling":         soort_regeling,
            "datum_inwerkingtreding": datum_iwtrd,
            "status":                 status,
            "wetgever":               wetgever,
            "url":                    url,
            "gevonden_op_zoekterm":   label,
        }

    except Exception as exc:
        logger.warning("Record kon niet worden geparsed: %s", exc)
        return None


def diagnose(cql_condition: str) -> dict:
    """
    Hulpfunctie om één query te testen zonder te pagineren.
    Geeft ruwe response-info terug voor debugging.
    """
    full_query = (
        f"({cql_condition})"
        f" AND ({GELDEND_FILTER})"
        f" AND ({TYPE_FILTER})"
    )
    params = {
        "operation":      "searchRetrieve",
        "version":        SRU_VERSION,
        "x-connection":   SRU_CONNECTION,
        "query":          full_query,
        "startRecord":    1,
        "maximumRecords": 1,
        "recordSchema":   "gzd",
    }
    resp = requests.get(SRU_BASE_URL, params=params, timeout=30)
    root = ET.fromstring(resp.content)
    total = _get_total(root)
    records = _get_records(root)

    first_parsed = None
    if records:
        first_parsed = _parse(records[0], label="diagnose")

    return {
        "status_code":   resp.status_code,
        "total_results": total,
        "first_record":  first_parsed,
        "raw_xml_snippet": resp.text[:2000],
    }
