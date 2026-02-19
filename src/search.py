"""
Zoekmodule: bevraagt de KOOP SRU API (Basis Wettenbestand) voor wetten.overheid.nl.

De SRU API geeft toegang tot het BWB (Basis Wettenbestand) en ondersteunt
CQL-queries (Contextual Query Language) met filtering op status 'geldend'.
"""

import time
import logging
from typing import Iterator
from xml.etree import ElementTree as ET

import requests

from src.config import SRU_BASE_URL, SRU_CONNECTION, SRU_MAX_RECORDS, REQUEST_DELAY_SECONDS

logger = logging.getLogger(__name__)

# CQL-filter: alleen geldende regelgeving
STATUS_FILTER = 'overheidbwb:geldigheidsstatus = "geldend"'

# XML namespaces in SRU-response
NS = {
    "srw": "http://www.loc.gov/zing/srw/",
    "gzd": "http://www.openarchives.org/OAI/2.0/",
    "dcterms": "http://purl.org/dc/terms/",
    "meta": "urn:overheidnl:metadata",
    "bwb": "bwb-dl",
    "overheidbwb": "http://standaarden.overheid.nl/bwb/",
}


def _build_cql_query(term: str) -> str:
    """Combineer zoekterm met filter voor geldende regelgeving."""
    return f'({term}) AND ({STATUS_FILTER})'


def _sru_request(cql_query: str, start_record: int = 1) -> ET.Element:
    """Voer één SRU-request uit en geef het XML-root element terug."""
    params = {
        "operation": "searchRetrieve",
        "x-connection": SRU_CONNECTION,
        "query": cql_query,
        "startRecord": start_record,
        "maximumRecords": SRU_MAX_RECORDS,
        "recordSchema": "gzd",
    }
    response = requests.get(SRU_BASE_URL, params=params, timeout=30)
    response.raise_for_status()
    return ET.fromstring(response.content)


def _extract_number_of_records(root: ET.Element) -> int:
    el = root.find(".//srw:numberOfRecords", NS)
    return int(el.text) if el is not None and el.text else 0


def _extract_records(root: ET.Element) -> list[ET.Element]:
    return root.findall(".//srw:record", NS)


def search_term(term: str) -> Iterator[dict]:
    """
    Zoek één term in het BWB. Pagineer automatisch door alle resultaten.
    Yield per gevonden wet een dict met basisinformatie.
    """
    cql = _build_cql_query(term)
    logger.info("Zoeken op: %s", term)

    # Eerste request om totaal te weten
    try:
        root = _sru_request(cql, start_record=1)
    except requests.RequestException as exc:
        logger.error("Request mislukt voor term '%s': %s", term, exc)
        return

    total = _extract_number_of_records(root)
    logger.info("  -> %d resultaten gevonden", total)

    records = _extract_records(root)
    for record in records:
        parsed = _parse_record(record, search_term=term)
        if parsed:
            yield parsed

    # Pagineer indien meer dan SRU_MAX_RECORDS resultaten
    start = SRU_MAX_RECORDS + 1
    while start <= total:
        time.sleep(REQUEST_DELAY_SECONDS)
        try:
            root = _sru_request(cql, start_record=start)
        except requests.RequestException as exc:
            logger.error("Paginering mislukt op start=%d: %s", start, exc)
            break
        for record in _extract_records(root):
            parsed = _parse_record(record, search_term=term)
            if parsed:
                yield parsed
        start += SRU_MAX_RECORDS


def _parse_record(record: ET.Element, search_term: str) -> dict | None:
    """Extraheer relevante velden uit één SRU-record."""
    try:
        # Zoek de recordData
        data = record.find(".//srw:recordData", NS)
        if data is None:
            return None

        def _find_text(path: str) -> str:
            el = data.find(path, NS)
            return el.text.strip() if el is not None and el.text else ""

        # BWB-identifier
        bwb_id = _find_text(".//meta:identifier")
        if not bwb_id:
            # Probeer alternatief pad
            bwb_id = _find_text(".//dcterms:identifier")

        titel = _find_text(".//meta:title") or _find_text(".//dcterms:title")
        citeertitel = _find_text(".//meta:alternative") or _find_text(".//dcterms:alternative")
        status = _find_text(".//overheidbwb:geldigheidsstatus")
        datum_inwerkingtreding = _find_text(".//meta:datumInwerkingtreding")
        soort_regeling = _find_text(".//meta:soortRegeling") or _find_text(".//meta:type")
        wetgever = _find_text(".//meta:creator") or _find_text(".//dcterms:creator")

        # URL op wetten.overheid.nl
        url = f"https://wetten.overheid.nl/{bwb_id}" if bwb_id else ""

        return {
            "bwb_id": bwb_id,
            "titel": titel,
            "citeertitel": citeertitel,
            "status": status,
            "datum_inwerkingtreding": datum_inwerkingtreding,
            "soort_regeling": soort_regeling,
            "wetgever": wetgever,
            "url": url,
            "gevonden_op_zoekterm": search_term,
        }

    except Exception as exc:
        logger.warning("Record kon niet worden geparsed: %s", exc)
        return None
