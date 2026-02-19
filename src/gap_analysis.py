"""
Manco-analyse: vergelijkt de gevonden regelgeving met ILT-publicaties.

Drie categorieën manco's:
1. Ongedekte taak     — wet wijst taak toe maar ILT rapporteert er niet over
2. Slapende bevoegdheid — ILT is bevoegd maar geen actief programma zichtbaar
3. Verouderde wettekst — wet noemt voorgangersministerie, opvolging onduidelijk
"""

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# Verwacht pad naar referentiebestand met ILT-bekende regelgeving
# (handmatig aan te vullen op basis van ILT Jaarplan / Jaarverslag)
REFERENCE_FILE = Path("data/reference/ilt_bekend_regelgeving.csv")

REFERENCE_COLUMNS = ["bwb_id", "titel", "bron"]  # bron: 'jaarplan', 'jaarverslag', etc.


def load_reference(path: Path = REFERENCE_FILE) -> set[str]:
    """
    Laad BWB-IDs van regelgeving die al bekend is bij ILT
    (afkomstig uit Jaarplan, Jaarverslag of handmatige invoer).
    Geeft een set van bwb_ids terug. Lege set als bestand ontbreekt.
    """
    if not path.exists():
        logger.warning(
            "Referentiebestand '%s' niet gevonden. "
            "Manco-analyse wordt uitgevoerd zonder ILT-referentie.",
            path,
        )
        return set()

    df = pd.read_csv(path, dtype=str)
    if "bwb_id" not in df.columns:
        logger.error("Referentiebestand mist kolom 'bwb_id'.")
        return set()

    known = set(df["bwb_id"].dropna().str.strip())
    logger.info("Referentiebestand geladen: %d bekende regelingen", len(known))
    return known


def analyse_gaps(
    inventory: pd.DataFrame,
    known_bwb_ids: set[str],
) -> pd.DataFrame:
    """
    Vergelijk de inventarisatie met de bekende regelgeving.
    Voeg kolom 'manco_categorie' toe.
    """
    results = []

    for _, row in inventory.iterrows():
        bwb_id = str(row.get("bwb_id", "")).strip()
        ministerie_type = str(row.get("ministerie_type", "")).lower()
        taaktypes = str(row.get("taaktypes", "")).lower()

        # Categorie 3: verouderde wettekst (historisch ministerie)
        if "historisch" in ministerie_type:
            row["manco_categorie"] = "verouderde_wettekst"
            row["manco_toelichting"] = (
                "Wet verwijst naar voorgangersministerie. "
                "Opvolging door ILT niet expliciet bevestigd."
            )

        # Categorie 1 & 2: niet in ILT-referentie
        elif bwb_id and bwb_id not in known_bwb_ids:
            if "toezicht" in taaktypes or "handhaving" in taaktypes:
                row["manco_categorie"] = "ongedekte_taak"
                row["manco_toelichting"] = (
                    "Wet wijst toezicht/handhavingstaak toe "
                    "maar niet aangetroffen in ILT-publicaties."
                )
            else:
                row["manco_categorie"] = "slapende_bevoegdheid"
                row["manco_toelichting"] = (
                    "ILT is mogelijk bevoegd maar geen actief toezichtprogramma "
                    "zichtbaar in ILT-publicaties."
                )

        else:
            row["manco_categorie"] = "gedekt"
            row["manco_toelichting"] = "Aanwezig in ILT-referentie."

        results.append(row)

    return pd.DataFrame(results)


def summarize_gaps(gap_df: pd.DataFrame) -> dict:
    """Geef een samenvatting van de manco-analyse."""
    counts = gap_df["manco_categorie"].value_counts().to_dict()
    total = len(gap_df)
    return {
        "totaal_gevonden": total,
        "gedekt": counts.get("gedekt", 0),
        "ongedekte_taak": counts.get("ongedekte_taak", 0),
        "slapende_bevoegdheid": counts.get("slapende_bevoegdheid", 0),
        "verouderde_wettekst": counts.get("verouderde_wettekst", 0),
    }
