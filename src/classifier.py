"""
Classificeert gevonden regelgeving naar ILT-domein en taaktype,
en registreert via welke zoeklaag de wet is gevonden.
"""

from src.config import ILT_DOMAINS, TASK_TYPES

# Ministeries die historisch zijn overgegaan in ILT/IenW
HISTORISCHE_MINISTERIES = {
    "verkeer en waterstaat":                                    "IenW-voorganger (V&W)",
    "volkshuisvesting, ruimtelijke ordening en milieubeheer":   "IenW-voorganger (VROM)",
    "infrastructuur en milieu":                                 "IenW-voorganger (IenM)",
    "vrom":                                                     "IenW-voorganger (VROM)",
    "inspectie verkeer en waterstaat":                          "ILT-voorganger (IVW)",
    "inspectie vrom":                                           "ILT-voorganger (IVROM)",
    "vrom-inspectie":                                           "ILT-voorganger (IVROM)",
    "inspectie ruimte en milieu":                               "ILT-voorganger (IRM)",
    "rijksluchtvaartdienst":                                    "ILT-voorganger (RLD)",
}


def classify_domain(record: dict) -> str:
    """
    Bepaal het ILT-domein op basis van titel en citeertitel.
    Geeft het eerste matchende domein terug, of 'Onbekend / nader te bepalen'.
    """
    text = f"{record.get('titel', '')} {record.get('citeertitel', '')}".lower()
    for domain_info in ILT_DOMAINS.values():
        for keyword in domain_info["keywords"]:
            if keyword.lower() in text:
                return domain_info["label"]

    # Fallback: kijk in de zoekterm (Laag 3 bevat het domein al in het label)
    label = record.get("gevonden_op_zoekterm", "")
    if label.startswith("[domein]"):
        # "[domein] luchtvaart + toezicht" → "luchtvaart"
        domain_hint = label.replace("[domein]", "").split("+")[0].strip().lower()
        for domain_info in ILT_DOMAINS.values():
            for keyword in domain_info["keywords"]:
                if keyword.lower() in domain_hint:
                    return domain_info["label"]

    return "Onbekend / nader te bepalen"


def classify_task_types(record: dict) -> list[str]:
    """Bepaal taaktypes op basis van titel, citeertitel én zoekterm."""
    text = (
        f"{record.get('titel', '')} "
        f"{record.get('citeertitel', '')} "
        f"{record.get('gevonden_op_zoekterm', '')}"
    ).lower()
    matched = []
    for task_type, keywords in TASK_TYPES.items():
        for kw in keywords:
            if kw.lower() in text:
                matched.append(task_type)
                break
    return matched if matched else ["onbekend"]


def classify_ministerie_type(record: dict) -> str:
    """
    Huidig ministerie (IenW) of historisch voorganger?
    Helpt bij identificatie van wetten met verouderde terminologie.
    """
    zoekterm = record.get("gevonden_op_zoekterm", "").lower()
    for historisch, label in HISTORISCHE_MINISTERIES.items():
        if historisch in zoekterm:
            return f"historisch ({label})"
    return "huidig"


def classify_search_layer(record: dict) -> str:
    """
    Registreer via welke zoeklaag de regeling is gevonden:
      Laag 1 — directe ILT-verwijzing
      Laag 2 — ministeriële toewijzing
      Laag 3 — domein + taakconstructie
    """
    label = record.get("gevonden_op_zoekterm", "")
    if label.startswith("[domein]"):
        return "Laag 3 (domein+taak)"
    lower = label.lower()
    if any(x in lower for x in ["inspectie", "ilt", "rijksluchtvaartdienst", "vrom-inspectie"]):
        return "Laag 1 (ILT-naam)"
    return "Laag 2 (ministerie)"


def classify_eu_grondslag(record: dict) -> bool:
    """Ruwe indicatie EU-grondslag op basis van titel."""
    text = f"{record.get('titel', '')} {record.get('citeertitel', '')}".lower()
    eu_indicatoren = [
        "implementatie", "richtlijn", "verordening", "eu-", "europese",
        "easa", "emsa", "era", "imo", "icao", "marpol", "solas",
    ]
    return any(ind in text for ind in eu_indicatoren)


def enrich_record(record: dict) -> dict:
    """Voeg alle classificaties toe aan een record."""
    record["ilt_domein"]             = classify_domain(record)
    record["taaktypes"]              = ", ".join(classify_task_types(record))
    record["ministerie_type"]        = classify_ministerie_type(record)
    record["gevonden_via_laag"]      = classify_search_layer(record)
    record["eu_grondslag_indicatie"] = classify_eu_grondslag(record)
    return record
