"""
ILT Wet- en Regelgeving Inventarisatie
=======================================
Zoekt systematisch naar alle geldende wet- en regelgeving in het BWB
(wetten.overheid.nl) waarbij ILT of een van haar voorgangersministeries
een taak is toebedeeld.

Gebruik:
    python main.py [--dry-run] [--terms ILT|MINISTERIES|TOEZICHT|ALL]

Opties:
    --dry-run       Voer alleen de eerste zoekterm uit (test)
    --terms         Welke categorie zoektermen gebruiken (default: ALL)
    --no-excel      Sla geen Excel op, alleen CSV
"""

import argparse
import logging
import sys
import time
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from src.config import (
    ALL_SEARCH_TERMS,
    SEARCH_TERMS_ILT,
    SEARCH_TERMS_MINISTERIES,
    SEARCH_TERMS_TOEZICHT,
    OUTPUT_CSV,
    OUTPUT_EXCEL,
    OUTPUT_GAPS,
)
from src.search import search_term
from src.classifier import enrich_record
from src.deduplicator import deduplicate
from src.gap_analysis import load_reference, analyse_gaps, summarize_gaps
from src.output import save_csv, save_excel

# Logging instellen
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("data/results/run.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

TERM_SETS = {
    "ILT": SEARCH_TERMS_ILT,
    "MINISTERIES": SEARCH_TERMS_MINISTERIES,
    "TOEZICHT": SEARCH_TERMS_TOEZICHT,
    "ALL": ALL_SEARCH_TERMS,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ILT regelgeving inventarisatie")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Voer alleen de eerste zoekterm uit (test)",
    )
    parser.add_argument(
        "--terms",
        choices=list(TERM_SETS.keys()),
        default="ALL",
        help="Welke categorie zoektermen gebruiken",
    )
    parser.add_argument(
        "--no-excel",
        action="store_true",
        help="Sla geen Excel op, alleen CSV",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    Path("data/results").mkdir(parents=True, exist_ok=True)

    terms = TERM_SETS[args.terms]
    if args.dry_run:
        terms = terms[:1]
        logger.info("DRY RUN: alleen eerste zoekterm wordt gebruikt")

    logger.info("Start inventarisatie met %d zoekterm(en)", len(terms))

    # --- Fase 1: Zoeken ---
    all_records: list[dict] = []
    for term in tqdm(terms, desc="Zoektermen"):
        try:
            for record in search_term(term):
                all_records.append(record)
            time.sleep(0.5)  # extra pauze tussen zoektermen
        except Exception as exc:
            logger.error("Fout bij zoekterm '%s': %s", term, exc)

    logger.info("Totaal gevonden (voor dedup): %d", len(all_records))

    if not all_records:
        logger.warning("Geen resultaten gevonden. Controleer verbinding met wetten.overheid.nl.")
        return

    # --- Fase 2: Deduplicatie ---
    unique_records = deduplicate(all_records)

    # --- Fase 3: Classificatie ---
    enriched = [enrich_record(r) for r in unique_records]
    inventory_df = pd.DataFrame(enriched)

    # --- Fase 4: Manco-analyse ---
    known_ids = load_reference()
    gap_df = analyse_gaps(inventory_df, known_ids)

    summary = summarize_gaps(gap_df)
    logger.info("=== Samenvatting manco-analyse ===")
    for key, val in summary.items():
        logger.info("  %-30s %d", key, val)

    # --- Fase 5: Output ---
    save_csv(gap_df, OUTPUT_CSV)
    save_csv(
        gap_df[gap_df["manco_categorie"] != "gedekt"],
        OUTPUT_GAPS,
    )

    if not args.no_excel:
        save_excel(gap_df, gap_df, OUTPUT_EXCEL)

    logger.info("Inventarisatie voltooid. Resultaten in: data/results/")


if __name__ == "__main__":
    main()
