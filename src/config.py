"""
Configuratie voor de ILT wet- en regelgeving inventarisatie.
"""

# --- SRU API ---
SRU_BASE_URL = "https://repository.officiele-overheidspublicaties.nl/sru"
SRU_CONNECTION = "BWB"
SRU_MAX_RECORDS = 100  # max per request
REQUEST_DELAY_SECONDS = 1.0  # respectvol crawlen

# --- Zoektermen ---
# Directe ILT-verwijzingen
SEARCH_TERMS_ILT = [
    '"Inspectie Leefomgeving en Transport"',
    '"Inspecteur-Generaal Leefomgeving en Transport"',
    '"ILT"',
]

# Ministeriele verwijzingen (huidig en historisch)
# Wetten verwijzen soms nog naar voorgangersministeries terwijl
# de taak via opvolgingsbesluit naar ILT is overgegaan.
SEARCH_TERMS_MINISTERIES = [
    '"Minister van Infrastructuur en Waterstaat"',
    '"Minister van Infrastructuur en Milieu"',
    '"Minister van Verkeer en Waterstaat"',
    '"Minister van Volkshuisvesting, Ruimtelijke Ordening en Milieubeheer"',
    '"Staatssecretaris van Infrastructuur en Waterstaat"',
    '"Staatssecretaris van Infrastructuur en Milieu"',
    '"Staatssecretaris van Verkeer en Waterstaat"',
    '"VROM"',
]

# Juridische constructies die toezichttaken aanduiden
SEARCH_TERMS_TOEZICHT = [
    '"aangewezen als toezichthouder"',
    '"belast met het toezicht"',
    '"toezicht op de naleving"',
    '"aangewezen ambtenaren"',
    '"bevoegd tot handhaving"',
]

# Gecombineerde lijst voor brede zoekstrategie
ALL_SEARCH_TERMS = SEARCH_TERMS_ILT + SEARCH_TERMS_MINISTERIES + SEARCH_TERMS_TOEZICHT

# --- ILT Toezichtdomeinen ---
ILT_DOMAINS = {
    "luchtvaart": {
        "keywords": ["luchtvaart", "luchtvaartuig", "luchtvaartmaatschappij",
                     "vliegtuig", "luchthaven", "EASA", "ICAO"],
        "label": "Luchtvaart",
    },
    "scheepvaart": {
        "keywords": ["scheepvaart", "schip", "vaartuig", "haven", "zeevaart",
                     "binnenvaart", "SOLAS", "MARPOL"],
        "label": "Scheepvaart",
    },
    "rail": {
        "keywords": ["spoorweg", "spoorwegen", "trein", "rail", "lokaal spoor",
                     "tram", "metro", "ERA"],
        "label": "Rail",
    },
    "wegvervoer": {
        "keywords": ["wegvervoer", "vrachtwagen", "autobus", "taxivervoer",
                     "rijtijden", "wegvoertuig", "tachograaf"],
        "label": "Wegvervoer",
    },
    "gevaarlijke_stoffen": {
        "keywords": ["gevaarlijke stoffen", "BRZO", "RIE", "Seveso",
                     "explosief", "ADR", "RID", "ADN", "vuurwerk",
                     "pyrotechnisch"],
        "label": "Gevaarlijke stoffen",
    },
    "milieu_leefomgeving": {
        "keywords": ["milieu", "omgeving", "bodem", "lucht", "geluid",
                     "afval", "meststof", "biociden", "bestrijdingsmiddelen",
                     "asbest", "energie", "emissie"],
        "label": "Milieu & Leefomgeving",
    },
    "bouw_producten": {
        "keywords": ["bouwproduct", "CE-markering", "bouwstof",
                     "drinkwater", "energielabel"],
        "label": "Bouw & Producten",
    },
}

# --- Taaktypes ---
TASK_TYPES = {
    "toezicht": ["toezicht", "inspectie", "controle", "surveillance"],
    "handhaving": ["handhaving", "bestuursdwang", "dwangsom", "boete",
                   "opleggen", "intrekking"],
    "vergunning": ["vergunning", "ontheffing", "certificaat", "erkenning",
                   "goedkeuring", "registratie"],
    "advies": ["advies", "aanbeveling", "signalering"],
    "certificering": ["certificering", "certificaat", "keurmerken", "typekeuring"],
}

# --- Output ---
OUTPUT_CSV = "data/results/ilt_regelgeving_inventarisatie.csv"
OUTPUT_EXCEL = "data/results/ilt_regelgeving_inventarisatie.xlsx"
OUTPUT_GAPS = "data/results/ilt_manco_analyse.csv"
