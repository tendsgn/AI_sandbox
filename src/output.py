"""
Output module: schrijft resultaten naar CSV en Excel.

Excel-structuur (drie tabs):
  1. Inventarisatie  — de volledige lijst van gevonden regelgeving
  2. Domeinoverzicht — tellingen per ILT-domein en soort regeling
  3. Manco analyse   — alleen de niet-gedekte regelgeving
"""

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# Kolomvolgorde voor de inventarisatie-export
EXPORT_COLUMNS = [
    "bwb_id",
    "titel",
    "citeertitel",
    "soort_regeling",
    "ilt_domein",
    "taaktypes",
    "ministerie_type",
    "eu_grondslag_indicatie",
    "datum_inwerkingtreding",
    "status",
    "url",
    "gevonden_op_zoektermen",
    "gevonden_via_laag",
    "manco_categorie",
    "manco_toelichting",
]

MANCO_COLORS = {
    "gedekt":               "C6EFCE",
    "ongedekte_taak":       "FFC7CE",
    "slapende_bevoegdheid": "FFEB9C",
    "verouderde_wettekst":  "BDD7EE",
}


def save_csv(df: pd.DataFrame, path: str) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cols = [c for c in EXPORT_COLUMNS if c in df.columns]
    df[cols].to_csv(output_path, index=False, encoding="utf-8-sig")
    logger.info("CSV opgeslagen: %s (%d rijen)", output_path, len(df))


def save_excel(df: pd.DataFrame, path: str) -> None:
    """
    Schrijf Excel met drie tabs:
    1. Inventarisatie  — volledige inventarisatie
    2. Domeinoverzicht — statistieken per domein
    3. Manco analyse   — alleen niet-gedekte regelgeving
    """
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cols = [c for c in EXPORT_COLUMNS if c in df.columns]
    mancos = df[df.get("manco_categorie", pd.Series()) != "gedekt"]
    if "manco_categorie" in df.columns:
        mancos = df[df["manco_categorie"] != "gedekt"].sort_values(
            ["manco_categorie", "ilt_domein"]
        )
    manco_cols = [c for c in EXPORT_COLUMNS if c in mancos.columns]

    domain_summary = _build_domain_summary(df)

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df[cols].to_excel(writer, sheet_name="Inventarisatie", index=False)
        domain_summary.to_excel(writer, sheet_name="Domeinoverzicht", index=False)
        mancos[manco_cols].to_excel(writer, sheet_name="Manco analyse", index=False)
        _apply_formatting(writer, df)

    logger.info("Excel opgeslagen: %s", output_path)


def _build_domain_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Bouw een overzichtstabel per ILT-domein:
    - Totaal aantal regelingen
    - Uitsplitsing per soort (wet, AMvB, ministeriële regeling, overig)
    - Uitsplitsing per taaktype
    - Aantal manco's per categorie
    """
    if "ilt_domein" not in df.columns:
        return pd.DataFrame()

    rows = []
    for domein in sorted(df["ilt_domein"].unique()):
        sub = df[df["ilt_domein"] == domein]

        soorten = sub["soort_regeling"].value_counts().to_dict() if "soort_regeling" in sub else {}

        mancos = {}
        if "manco_categorie" in sub.columns:
            mancos = sub["manco_categorie"].value_counts().to_dict()

        rows.append({
            "ilt_domein":            domein,
            "totaal_regelingen":     len(sub),
            "wet":                   soorten.get("wet", 0),
            "amvb":                  soorten.get("AMvB", soorten.get("amvb", 0)),
            "min_regeling":          soorten.get("ministeriële regeling",
                                                  soorten.get("MR", 0)),
            "overig":                sum(
                v for k, v in soorten.items()
                if k.lower() not in ("wet", "amvb", "ministeriële regeling", "mr")
            ),
            "gedekt":                mancos.get("gedekt", 0),
            "ongedekte_taak":        mancos.get("ongedekte_taak", 0),
            "slapende_bevoegdheid":  mancos.get("slapende_bevoegdheid", 0),
            "verouderde_wettekst":   mancos.get("verouderde_wettekst", 0),
        })

    return pd.DataFrame(rows).sort_values("totaal_regelingen", ascending=False)


def _apply_formatting(writer: pd.ExcelWriter, df: pd.DataFrame) -> None:
    try:
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl.utils import get_column_letter

        for sheet_name in writer.sheets:
            ws = writer.sheets[sheet_name]

            # Header vet + bevroren rij
            for cell in ws[1]:
                cell.font = Font(bold=True)
                cell.alignment = Alignment(wrap_text=True)
            ws.freeze_panes = "A2"

            # Auto-breedte (max 60)
            for col_idx, col in enumerate(ws.columns, 1):
                max_len = max(
                    (len(str(cell.value or "")) for cell in col), default=10
                )
                ws.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 2, 60)

            # Rijkleuring op manco_categorie voor manco-tab
            if sheet_name == "Manco analyse":
                header = [cell.value for cell in ws[1]]
                if "manco_categorie" in header:
                    manco_col = header.index("manco_categorie") + 1
                    for row in ws.iter_rows(min_row=2):
                        manco_val = str(row[manco_col - 1].value or "")
                        color = MANCO_COLORS.get(manco_val, "FFFFFF")
                        fill = PatternFill(fill_type="solid", fgColor=color)
                        for cell in row:
                            cell.fill = fill

    except ImportError:
        logger.warning("openpyxl styles niet beschikbaar, opmaak overgeslagen.")
