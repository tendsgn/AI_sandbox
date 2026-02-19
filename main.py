"""
ILT Wet- en Regelgeving Inventarisatie
=======================================
Inventariseert systematisch alle geldende wet- en regelgeving waarbij ILT
of een van haar rechtsvoorgangers een taak heeft toebedeeld gekregen.

API: KOOP SRU — zoekservice.overheid.nl (Basis Wettenbestand)
Documentatie: https://data.overheid.nl/dataset/basis-wetten-bestand

Zoekstrategie (twee lagen):
  Laag 1 — overheid.authority: alle geldende regelgeving waarbij IenW of
            een voorgangersministerie als bevoegd gezag is geregistreerd.
  Laag 2 — keyword: aanvullende zoekslag per ILT-domein, pakt regelgeving
            op die onder een ander ministerie valt maar waarbij ILT een rol heeft.

De manco-analyse (additionele uitvoer) vergelijkt de inventarisatie met
bekende ILT-publicaties om niet-gerapporteerde taken zichtbaar te maken.

Gebruik:
    python main.py [--dry-run] [--layers 1 2] [--no-excel]

    --dry-run     Test: voert slechts één query per laag uit
    --layers      Welke lagen activeren (default: 1 2)
    --no-excel    Sla geen Excel op, alleen CSV
"""

import argparse
import logging
import sys
import time
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from src.config import (
    AUTHORITY_QUERIES,
    KEYWORD_QUERIES,
    OUTPUT_CSV,
    OUTPUT_EXCEL,
    OUTPUT_GAPS,
)
from src.search import search
from src.classifier import enrich_record
from src.deduplicator import deduplicate
from src.gap_analysis import load_reference, analyse_gaps, summarize_gaps
from src.output import save_csv, save_excel

Path("data/results").mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("data/results/run.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="ILT wet- en regelgeving inventarisatie"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Test: slechts één query per laag uitvoeren",
    )
    parser.add_argument(
        "--layers",
        nargs="+",
        type=int,
        choices=[1, 2],
        default=[1, 2],
        help="Welke zoeklagen activeren (1=authority, 2=keyword)",
    )
    parser.add_argument(
        "--no-excel",
        action="store_true",
        help="Sla geen Excel op, alleen CSV",
    )
    return parser.parse_args()


def run_layer_1(dry_run: bool) -> list[dict]:
    """
    Laag 1: filter op verantwoordelijk ministerie (overheid.authority).
    Geeft alle geldende wet/AMvB/MR terug voor IenW en voorgangers.
    """
    queries = AUTHORITY_QUERIES[:1] if dry_run else AUTHORITY_QUERIES
    records: list[dict] = []
    logger.info("=== Laag 1: bevoegd gezag (%d queries) ===", len(queries))
    for cql in tqdm(queries, desc="Laag 1"):
        # Gebruik het ministerie zelf als leesbaar label
        label = cql.replace('overheid.authority = ', '').strip('"')
        try:
            for r in search(cql, label=f"[authority] {label}"):
                records.append(r)
            time.sleep(0.5)
        except Exception as exc:
            logger.error("Fout bij '%s': %s", cql, exc)
    logger.info("Laag 1: %d records (voor dedup)", len(records))
    return records


def run_layer_2(dry_run: bool) -> list[dict]:
    """
    Laag 2: keyword-zoekopdrachten per ILT-domein.
    Pakt regelgeving op die qua ministry buiten Laag 1 valt.
    """
    queries = KEYWORD_QUERIES[:1] if dry_run else KEYWORD_QUERIES
    records: list[dict] = []
    logger.info("=== Laag 2: keyword per domein (%d queries) ===", len(queries))
    for cql in tqdm(queries, desc="Laag 2"):
        label = cql.replace('keyword = ', '').strip('"')
        try:
            for r in search(cql, label=f"[keyword] {label}"):
                records.append(r)
            time.sleep(0.5)
        except Exception as exc:
            logger.error("Fout bij '%s': %s", cql, exc)
    logger.info("Laag 2: %d records (voor dedup)", len(records))
    return records


def main() -> None:
    args = parse_args()

    all_raw: list[dict] = []

    if 1 in args.layers:
        all_raw.extend(run_layer_1(args.dry_run))
    if 2 in args.layers:
        all_raw.extend(run_layer_2(args.dry_run))

    logger.info("Totaal gevonden (voor dedup): %d", len(all_raw))

    if not all_raw:
        logger.warning(
            "Geen resultaten. Controleer verbinding en API-endpoint.\n"
            "Tip: voer 'python diagnose.py' uit om de API te testen."
        )
        return

    # Deduplicatie
    unique = deduplicate(all_raw)

    # Classificatie
    enriched = [enrich_record(r) for r in unique]
    inventory_df = pd.DataFrame(enriched)

    # Samenvatting per domein
    per_domein = inventory_df.groupby("ilt_domein").size().sort_values(ascending=False)
    logger.info("=== Regelingen per domein (na dedup) ===")
    for domein, n in per_domein.items():
        logger.info("  %-35s %d", domein, n)

    # Manco-analyse (additioneel)
    known_ids = load_reference()
    gap_df = analyse_gaps(inventory_df, known_ids)
    summary = summarize_gaps(gap_df)
    logger.info("=== Manco-samenvatting ===")
    logger.info("  Totaal unieke regelingen: %d", summary["totaal_gevonden"])
    logger.info("  Gedekt in ILT-referentie: %d", summary["gedekt"])
    logger.info("  Ongedekte taken:          %d", summary["ongedekte_taak"])
    logger.info("  Slapende bevoegdheden:    %d", summary["slapende_bevoegdheid"])
    logger.info("  Verouderde wettekst:      %d", summary["verouderde_wettekst"])

    # Output
    save_csv(gap_df, OUTPUT_CSV)
    if "manco_categorie" in gap_df.columns:
        manco_df = gap_df[gap_df["manco_categorie"] != "gedekt"]
        save_csv(manco_df, OUTPUT_GAPS)
    if not args.no_excel:
        save_excel(gap_df, OUTPUT_EXCEL)

    logger.info("Klaar. Resultaten in: data/results/")


if __name__ == "__main__":
    main()
