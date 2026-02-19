"""
Zoekmodule: bevraagt de KOOP SRU API voor het Basis Wettenbestand (BWB).

Eindpunt:  https://zoekservice.overheid.nl/sru/Search
Protocol:  SRU 1.2
Collectie: BWB (Basis Wettenbestand)
Formaat:   XML (GZD-schema, standaard server-response zonder recordSchema-param)

Namespaces in de response (geverifieerd via explain + stap-2-query):
  SRW:         http://www.loc.gov/zing/srw/
  GZD:         http://standaarden.overheid.nl/sru
  dcterms:     http://purl.org/dc/terms/
  overheid:    http://standaarden.overheid.nl/owms/terms/
  overheidbwb: http://standaarden.overheid.nl/bwb/terms/

XML-structuur per record:
  srw:record / srw:recordData / gzd:gzd / gzd:originalData
    / overheidbwb:meta / owmskern
      dcterms:identifier, dcterms:title, dcterms:type, dcterms:creator,
      overheid:authority, dcterms:modified
    / owmsmantel
      dcterms:created
    / bwbipm
      overheidbwb:geldigheidsperiode_startdatum
      overheidbwb:geldigheidsperiode_einddatum   ← "9999-12-31" = geldend

Beperkingen:
  - Zoekt ALLEEN op metadata, niet op wettekst.
  - Maximaal 50 records per request.
  - overheidbwb.geldigheidsstatus bestaat NIET als CQL-index (fout 1/16).
    Geldend-filtering vindt post-hoc plaats op geldigheidsperiode_einddatum.

Bruikbare CQL-velden (BWB, geverifieerd via explain):
  overheid.authority    Verantwoordelijk ministerie
  dcterms.type          wet / AMvB / ministeriele-regeling / KB
  dcterms.identifier    BWB-identifier (exact)
  dcterms.modified      Datum laatste wijziging
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
)

logger = logging.getLogger(__name__)

# Exacte namespace-URIs zoals teruggegeven door de server (geverifieerd via diagnose.py)
_NS = {
    "srw":          "http://www.loc.gov/zing/srw/",
    "gzd":          "http://standaarden.overheid.nl/sru",
    "dcterms":      "http://purl.org/dc/terms/",
    "overheid":     "http://standaarden.overheid.nl/owms/terms/",
    "overheidbwb":  "http://standaarden.overheid.nl/bwb/terms/",
}

# Vaste tag-strings (Clark-notatie) voor veelgebruikte elementen
_T = {k: "{" + v + "}" for k, v in _NS.items()}

# Datum-sentinel voor open-einde geldigheid
_OPEN_EINDDATUM = "9999-12-31"


# ---------------------------------------------------------------------------
# Publieke interface
# ---------------------------------------------------------------------------

def search(cql_condition: str, label: str) -> Iterator[dict]:
    """
    Voer een CQL-zoekopdracht uit op het BWB en yield geldende records.

    cql_condition: het specifieke zoekcriterium,
                   bijv. 'overheid.authority = "Infrastructuur en Waterstaat"'
    label:         beschrijving voor logging en output-kolom

    Geldend-filtering (overheidbwb.geldigheidsstatus bestaat niet als CQL-index)
    vindt post-hoc plaats: alleen records met geldigheidsperiode_einddatum =
    "9999-12-31" worden doorgegeven.
    """
    yield from _paginate(cql_condition, label=label)


# ---------------------------------------------------------------------------
# Interne helpers
# ---------------------------------------------------------------------------

def _paginate(cql_query: str, label: str) -> Iterator[dict]:
    """Voer een volledige query uit inclusief automatische paginering."""
    logger.info("Zoeken: %s", label)
    try:
        root = _request(cql_query, start_record=1)
    except requests.RequestException as exc:
        logger.error("Request mislukt voor '%s': %s", label, exc)
        return

    total = _get_total(root)
    logger.info("  -> %d resultaten (voor geldend-filter)", total)
    if total == 0:
        return

    yielded = 0
    for rec in _get_records(root):
        parsed = _parse(rec, label)
        if parsed:
            yielded += 1
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
                yielded += 1
                yield parsed
        start += SRU_MAX_RECORDS

    logger.info("  -> %d geldende records doorgegeven", yielded)


def _request(cql_query: str, start_record: int = 1) -> ET.Element:
    """
    Stuur één SRU searchRetrieve-request.

    recordSchema wordt NIET meegegeven: de server geeft dan standaard GZD-XML
    terug. recordSchema=gzd veroorzaakte fout 1/67 (schema known but record
    cannot be transformed).
    """
    params = {
        "operation":      "searchRetrieve",
        "version":        SRU_VERSION,
        "x-connection":   SRU_CONNECTION,
        "query":          cql_query,
        "startRecord":    start_record,
        "maximumRecords": SRU_MAX_RECORDS,
    }
    resp = requests.get(SRU_BASE_URL, params=params, timeout=30)
    resp.raise_for_status()
    return ET.fromstring(resp.content)


def _get_total(root: ET.Element) -> int:
    """Lees numberOfRecords uit de SRU-response."""
    el = root.find(f".//{_T['srw']}numberOfRecords")
    if el is not None and el.text:
        try:
            return int(el.text.strip())
        except ValueError:
            pass
    return 0


def _get_records(root: ET.Element) -> list[ET.Element]:
    """Geef alle srw:record-elementen in de response."""
    return root.findall(f".//{_T['srw']}record")


def _txt(element: ET.Element, clark_tag: str) -> str:
    """Geef de tekstinhoud van het eerste overeenkomende element, of ''."""
    el = element.find(".//" + clark_tag)
    if el is not None and el.text:
        return el.text.strip()
    return ""


def _parse(record: ET.Element, label: str) -> dict | None:
    """
    Extraheer metadata uit één SRU-record en pas geldend-filter toe.

    Retourneert None als:
    - recordData niet gevonden
    - bwb_id én titel ontbreken
    - geldigheidsperiode_einddatum != "9999-12-31" (niet meer geldend)
    """
    try:
        data = record.find(f".//{_T['srw']}recordData")
        if data is None:
            return None

        bwb_id         = _txt(data, _T["dcterms"] + "identifier")
        titel          = _txt(data, _T["dcterms"] + "title")
        soort_regeling = _txt(data, _T["dcterms"] + "type")
        wetgever       = _txt(data, _T["dcterms"] + "creator")
        authority      = _txt(data, _T["overheid"] + "authority")
        datum_modified = _txt(data, _T["dcterms"] + "modified")
        datum_created  = _txt(data, _T["dcterms"] + "created")
        einddatum      = _txt(data, _T["overheidbwb"] + "geldigheidsperiode_einddatum")
        startdatum     = _txt(data, _T["overheidbwb"] + "geldigheidsperiode_startdatum")

        # Post-hoc geldend-filter: alleen open-einde records
        if einddatum and einddatum != _OPEN_EINDDATUM:
            return None

        if not titel and not bwb_id:
            return None

        url = f"https://wetten.overheid.nl/{bwb_id}" if bwb_id else ""

        return {
            "bwb_id":                 bwb_id,
            "titel":                  titel,
            "soort_regeling":         soort_regeling,
            "wetgever":               wetgever,
            "authority":              authority,
            "datum_inwerkingtreding": datum_created or startdatum,
            "datum_gewijzigd":        datum_modified,
            "url":                    url,
            "gevonden_op_zoekterm":   label,
        }

    except Exception as exc:
        logger.warning("Record kon niet worden geparsed: %s", exc)
        return None


def diagnose(cql_condition: str) -> dict:
    """
    Hulpfunctie om één query te testen zonder te pagineren.
    Gebruik het standalone diagnose.py voor uitgebreidere stap-voor-stap tests.
    """
    params = {
        "operation":      "searchRetrieve",
        "version":        SRU_VERSION,
        "x-connection":   SRU_CONNECTION,
        "query":          cql_condition,
        "startRecord":    1,
        "maximumRecords": 1,
    }
    resp = requests.get(SRU_BASE_URL, params=params, timeout=30)
    root = ET.fromstring(resp.content)
    total = _get_total(root)
    records = _get_records(root)

    first_parsed = None
    if records:
        first_parsed = _parse(records[0], label="diagnose")

    return {
        "status_code":     resp.status_code,
        "total_results":   total,
        "first_record":    first_parsed,
        "raw_xml_snippet": resp.text[:2000],
    }
