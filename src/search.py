"""
Zoekmodule: bevraagt de KOOP SRU API (Basis Wettenbestand) voor wetten.overheid.nl.

Ondersteunt twee zoekvormen:
  1. Enkelvoudige zoekterm (Laag 1 & 2): zoek op naam/instantie
  2. Domeinpaar (Laag 3): zoek op (domeinterm, taakterm) als CQL AND-combinatie

De API geeft alleen geldende regelgeving terug (filter: status = geldend).
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
    "dcterms": "http://purl.org/dc/terms/",
    "meta": "urn:overheidnl:metadata",
    "overheidbwb": "http://standaarden.overheid.nl/bwb/",
}


# ---------------------------------------------------------------------------
# Publieke interface
# ---------------------------------------------------------------------------

def search_term(term: str) -> Iterator[dict]:
    """
    Enkelvoudige zoekterm (Laag 1 & 2).
    Zoek op een exacte string in de volledige tekst van het BWB.
    """
    cql = f'({term}) AND ({STATUS_FILTER})'
    yield from _paginate(cql, label=term)


def search_domain_pair(domain_term: str, task_term: str) -> Iterator[dict]:
    """
    Domeinpaar (Laag 3).
    Zoekt op combinatie van domein-sleutelwoord EN taak-sleutelwoord.
    Label toont beide termen voor herleidbaarheid in de output.
    """
    cql = f'("{domain_term}" AND "{task_term}") AND ({STATUS_FILTER})'
    label = f'[domein] {domain_term} + {task_term}'
    yield from _paginate(cql, label=label)


# ---------------------------------------------------------------------------
# Interne helpers
# ---------------------------------------------------------------------------

def _paginate(cql: str, label: str) -> Iterator[dict]:
    """Voer een CQL-query uit en pagineer automatisch door alle resultaten."""
    logger.info("Zoeken: %s", label)
    try:
        root = _sru_request(cql, start_record=1)
    except requests.RequestException as exc:
        logger.error("Request mislukt voor '%s': %s", label, exc)
        return

    total = _extract_number_of_records(root)
    logger.info("  -> %d resultaten", total)

    for record in _extract_records(root):
        parsed = _parse_record(record, search_label=label)
        if parsed:
            yield parsed

    start = SRU_MAX_RECORDS + 1
    while start <= total:
        time.sleep(REQUEST_DELAY_SECONDS)
        try:
            root = _sru_request(cql, start_record=start)
        except requests.RequestException as exc:
            logger.error("Paginering mislukt (start=%d) voor '%s': %s", start, label, exc)
            break
        for record in _extract_records(root):
            parsed = _parse_record(record, search_label=label)
            if parsed:
                yield parsed
        start += SRU_MAX_RECORDS


def _sru_request(cql_query: str, start_record: int = 1) -> ET.Element:
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


def _parse_record(record: ET.Element, search_label: str) -> dict | None:
    try:
        data = record.find(".//srw:recordData", NS)
        if data is None:
            return None

        def _find_text(path: str) -> str:
            el = data.find(path, NS)
            return el.text.strip() if el is not None and el.text else ""

        bwb_id = _find_text(".//meta:identifier") or _find_text(".//dcterms:identifier")
        titel = _find_text(".//meta:title") or _find_text(".//dcterms:title")
        citeertitel = _find_text(".//meta:alternative") or _find_text(".//dcterms:alternative")
        status = _find_text(".//overheidbwb:geldigheidsstatus")
        datum_inwerkingtreding = _find_text(".//meta:datumInwerkingtreding")
        soort_regeling = _find_text(".//meta:soortRegeling") or _find_text(".//meta:type")
        wetgever = _find_text(".//meta:creator") or _find_text(".//dcterms:creator")

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
            "gevonden_op_zoekterm": search_label,
        }

    except Exception as exc:
        logger.warning("Record kon niet worden geparsed: %s", exc)
        return None
