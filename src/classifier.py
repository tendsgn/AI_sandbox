"""
Classificeert gevonden regelgeving naar ILT-domein en taaktype.
"""

from src.config import ILT_DOMAINS, TASK_TYPES

# Ministeries die historisch zijn overgegaan in ILT/IenW
HISTORISCHE_MINISTERIES = {
    "Verkeer en Waterstaat": "IenW-voorganger",
    "Volkshuisvesting, Ruimtelijke Ordening en Milieubeheer": "IenW-voorganger (VROM)",
    "Infrastructuur en Milieu": "IenW-voorganger",
    "VROM": "IenW-voorganger (VROM)",
}


def classify_domain(record: dict) -> str:
    """
    Bepaal het ILT-domein op basis van titel en citeertitel.
    Geeft het eerste matchende domein terug, of 'onbekend'.
    """
    text = f"{record.get('titel', '')} {record.get('citeertitel', '')}".lower()
    for domain_key, domain_info in ILT_DOMAINS.items():
        for keyword in domain_info["keywords"]:
            if keyword.lower() in text:
                return domain_info["label"]
    return "Onbekend / nader te bepalen"


def classify_task_types(record: dict) -> list[str]:
    """
    Bepaal alle taaktypes op basis van titel en citeertitel.
    Meerdere taaktypes per wet zijn mogelijk.
    """
    text = f"{record.get('titel', '')} {record.get('citeertitel', '')}".lower()
    matched = []
    for task_type, keywords in TASK_TYPES.items():
        for kw in keywords:
            if kw.lower() in text:
                matched.append(task_type)
                break
    return matched if matched else ["onbekend"]


def classify_ministerie_type(record: dict) -> str:
    """
    Bepaal of de wet verwijst naar het huidige ministerie of een historisch voorganger.
    Dit helpt bij het identificeren van wetten die formeel nog 'oud' taalgebruik bevatten.
    """
    zoekterm = record.get("gevonden_op_zoekterm", "")
    for historisch, label in HISTORISCHE_MINISTERIES.items():
        if historisch.lower() in zoekterm.lower():
            return f"historisch ({label})"
    return "huidig"


def classify_eu_grondslag(record: dict) -> bool:
    """
    Indicatie of de wet mogelijk een EU-grondslag heeft (ruwe heuristiek op titel).
    """
    text = f"{record.get('titel', '')} {record.get('citeertitel', '')}".lower()
    eu_indicatoren = ["implementatie", "richtlijn", "verordening", "eu-", "europese",
                      "easa", "emsa", "era", "imo", "icao"]
    return any(ind in text for ind in eu_indicatoren)


def enrich_record(record: dict) -> dict:
    """Voeg classificaties toe aan een record."""
    record["ilt_domein"] = classify_domain(record)
    record["taaktypes"] = ", ".join(classify_task_types(record))
    record["ministerie_type"] = classify_ministerie_type(record)
    record["eu_grondslag_indicatie"] = classify_eu_grondslag(record)
    return record
