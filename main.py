"""
ILT Wet- en Regelgeving Inventarisatie
=======================================
Inventariseert systematisch alle geldende wet- en regelgeving waarbij ILT
of een van haar rechtsvoorgangers een taak heeft toebedeeld gekregen.

Zoekstrategie (drie lagen):
  Laag 1 — directe ILT-verwijzingen (naam van ILT of voorganger expliciet)
  Laag 2 — ministeriële toewijzing (IenW / IenM / V&W / VROM + taakconstructie)
  Laag 3 — domein + taakterm (vindt wetten die 'de Minister' noemen zonder naam)

De manco-analyse vergelijkt de complete inventarisatie vervolgens met bekende
ILT-publicaties om te laten zien waar ILT aantoonbaar taken niet rapporteert.

Gebruik:
    python main.py [opties]

Opties:
    --dry-run         Voer alleen de eerste term per laag uit (test)
    --layers 1 2 3    Welke zoeklagen gebruiken (default: alle drie)
    --no-excel        Sla geen Excel op, alleen CSV
"""

import argparse
import logging
import sys
import time
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from src.config import (
    SEARCH_TERMS_ILT,
    SEARCH_TERMS_MINISTERIES,
    SEARCH_TERMS_DOMEINEN,
    OUTPUT_CSV,
    OUTPUT_EXCEL,
    OUTPUT_GAPS,
)
from src.search import search_term, search_domain_pair
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
        help="Voer alleen de eerste term per laag uit (test)",
    )
    parser.add_argument(
        "--layers",
        nargs="+",
        type=int,
        choices=[1, 2, 3],
        default=[1, 2, 3],
        help="Welke zoeklagen activeren (1=ILT, 2=ministeries, 3=domein+taak)",
    )
    parser.add_argument(
        "--no-excel",
        action="store_true",
        help="Sla geen Excel op, alleen CSV",
    )
    return parser.parse_args()


def run_layer_1(dry_run: bool) -> list[dict]:
    """Laag 1: directe ILT-verwijzingen."""
    terms = SEARCH_TERMS_ILT[:1] if dry_run else SEARCH_TERMS_ILT
    records: list[dict] = []
    logger.info("=== Laag 1: directe ILT-verwijzingen (%d termen) ===", len(terms))
    for term in tqdm(terms, desc="Laag 1"):
        try:
            for r in search_term(term):
                records.append(r)
            time.sleep(0.5)
        except Exception as exc:
            logger.error("Fout bij '%s': %s", term, exc)
    logger.info("Laag 1: %d records", len(records))
    return records


def run_layer_2(dry_run: bool) -> list[dict]:
    """Laag 2: ministeriële toewijzing."""
    terms = SEARCH_TERMS_MINISTERIES[:1] if dry_run else SEARCH_TERMS_MINISTERIES
    records: list[dict] = []
    logger.info("=== Laag 2: ministeriële toewijzing (%d termen) ===", len(terms))
    for term in tqdm(terms, desc="Laag 2"):
        try:
            for r in search_term(term):
                records.append(r)
            time.sleep(0.5)
        except Exception as exc:
            logger.error("Fout bij '%s': %s", term, exc)
    logger.info("Laag 2: %d records", len(records))
    return records


def run_layer_3(dry_run: bool) -> list[dict]:
    """Laag 3: domein + taakconstructie."""
    pairs = SEARCH_TERMS_DOMEINEN[:1] if dry_run else SEARCH_TERMS_DOMEINEN
    records: list[dict] = []
    logger.info("=== Laag 3: domein + taakconstructie (%d combinaties) ===", len(pairs))
    for domain_term, task_term in tqdm(pairs, desc="Laag 3"):
        try:
            for r in search_domain_pair(domain_term, task_term):
                records.append(r)
            time.sleep(0.5)
        except Exception as exc:
            logger.error("Fout bij ('%s', '%s'): %s", domain_term, task_term, exc)
    logger.info("Laag 3: %d records", len(records))
    return records


def main() -> None:
    args = parse_args()

    all_raw: list[dict] = []

    if 1 in args.layers:
        all_raw.extend(run_layer_1(args.dry_run))
    if 2 in args.layers:
        all_raw.extend(run_layer_2(args.dry_run))
    if 3 in args.layers:
        all_raw.extend(run_layer_3(args.dry_run))

    logger.info("Totaal gevonden (voor dedup): %d", len(all_raw))

    if not all_raw:
        logger.warning(
            "Geen resultaten gevonden. Controleer verbinding met wetten.overheid.nl."
        )
        return

    # --- Deduplicatie ---
    unique = deduplicate(all_raw)

    # --- Classificatie ---
    enriched = [enrich_record(r) for r in unique]
    inventory_df = pd.DataFrame(enriched)

    # --- Manco-analyse (additioneel, niet het hoofdproduct) ---
    known_ids = load_reference()
    gap_df = analyse_gaps(inventory_df, known_ids)

    summary = summarize_gaps(gap_df)
    logger.info("=== Samenvatting ===")
    logger.info("  Totaal unieke regelingen: %d", summary["totaal_gevonden"])
    logger.info("  Gedekt in ILT-referentie: %d", summary["gedekt"])
    logger.info("  Ongedekte taken:          %d", summary["ongedekte_taak"])
    logger.info("  Slapende bevoegdheden:    %d", summary["slapende_bevoegdheid"])
    logger.info("  Verouderde wettekst:      %d", summary["verouderde_wettekst"])

    per_domein = gap_df.groupby("ilt_domein").size().sort_values(ascending=False)
    logger.info("=== Regelingen per domein ===")
    for domein, n in per_domein.items():
        logger.info("  %-35s %d", domein, n)

    # --- Output ---
    # Primaire output: de volledige inventarisatie
    save_csv(gap_df, OUTPUT_CSV)

    # Secundaire output: alleen manco's
    if "manco_categorie" in gap_df.columns:
        manco_df = gap_df[gap_df["manco_categorie"] != "gedekt"]
        save_csv(manco_df, OUTPUT_GAPS)

    if not args.no_excel:
        save_excel(gap_df, OUTPUT_EXCEL)

    logger.info("Klaar. Resultaten in: data/results/")


if __name__ == "__main__":
    main()
