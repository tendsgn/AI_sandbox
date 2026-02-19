"""
Configuratie voor de ILT wet- en regelgeving inventarisatie.

Zoekstrategie (drie lagen, alle geldende regelgeving):
  Laag 1 – Directe ILT-verwijzingen: wet noemt ILT of IGLT expliciet
  Laag 2 – Ministeriële toewijzing: wet noemt IenW/IenM/V&W/VROM + taakconstructie
  Laag 3 – Domein + taak: wet regelt een ILT-domein én bevat een toezicht/handha-
            vingsconstructie (vindt ook wetten die 'de Minister' noemen zonder naam)
"""

# --- SRU API ---
SRU_BASE_URL = "https://repository.officiele-overheidspublicaties.nl/sru"
SRU_CONNECTION = "BWB"
SRU_MAX_RECORDS = 100  # max per request
REQUEST_DELAY_SECONDS = 1.0  # respectvol crawlen

# ===========================================================================
# LAAG 1 — Directe ILT-verwijzingen
# ===========================================================================
SEARCH_TERMS_ILT = [
    '"Inspectie Leefomgeving en Transport"',
    '"Inspecteur-Generaal Leefomgeving en Transport"',
    '"ILT"',
    '"Inspectie Verkeer en Waterstaat"',      # voorganger ILT (vóór 2012)
    '"Inspectie VROM"',                        # voorganger ILT
    '"VROM-Inspectie"',
    '"Inspectie Ruimte en Milieu"',            # voorganger ILT
    '"Rijksluchtvaartdienst"',                 # RLD, opgegaan in IVW → ILT
]

# ===========================================================================
# LAAG 2 — Ministeriële toewijzing
# Huidig en historisch. Wetten kunnen nog naam voorganger bevatten terwijl
# het Instellingsbesluit ILT de taak heeft overgedragen.
# ===========================================================================
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

# ===========================================================================
# LAAG 3 — Domein + taakconstructie
# Vindt wetten in ILT-domeinen die een inspectie/toezicht/handhavings-
# taak bevatten, ongeacht welke instantie bij name wordt genoemd.
# Combinaties worden als CQL opgebouwd door de zoekmodule.
# ===========================================================================
SEARCH_TERMS_DOMEINEN: list[tuple[str, str]] = [
    # (domein-zoekterm, taak-zoekterm)  → CQL: term_a AND term_b
    # Luchtvaart
    ("luchtvaart",          "toezicht"),
    ("luchtvaart",          "handhaving"),
    ("luchtvaart",          "certificering"),
    ("luchtvaartuig",       "inspectie"),
    ("luchthaven",          "toezicht"),
    ("luchthaven",          "vergunning"),
    ("luchtvaartmaatschappij", "vergunning"),
    ("burgerluchthaven",    "toezicht"),
    # Scheepvaart
    ("scheepvaart",         "toezicht"),
    ("scheepvaart",         "handhaving"),
    ("scheepvaart",         "certificering"),
    ("zeevaart",            "toezicht"),
    ("binnenvaart",         "toezicht"),
    ("binnenvaart",         "handhaving"),
    ("vaartuig",            "keuring"),
    ("haven",               "handhaving"),
    # Rail
    ("spoorwegen",          "toezicht"),
    ("spoorwegen",          "handhaving"),
    ("spoorweg",            "veiligheid"),
    ("lokaalspoor",         "toezicht"),
    ("tram",                "toezicht"),
    ("metro",               "toezicht"),
    # Wegvervoer
    ("wegvervoer",          "toezicht"),
    ("wegvervoer",          "handhaving"),
    ("taxivervoer",         "toezicht"),
    ("taxivervoer",         "vergunning"),
    ("autobus",             "vergunning"),
    ("rijtijden",           "handhaving"),
    ("tachograaf",          "toezicht"),
    ("cabotage",            "handhaving"),
    # Gevaarlijke stoffen
    ("gevaarlijke stoffen", "toezicht"),
    ("gevaarlijke stoffen", "handhaving"),
    ("BRZO",                "toezicht"),
    ("vuurwerk",            "toezicht"),
    ("vuurwerk",            "vergunning"),
    ("pyrotechnisch",       "toezicht"),
    ("explosief",           "toezicht"),
    ("ADR",                 "handhaving"),
    # Milieu & Leefomgeving
    ("asbest",              "toezicht"),
    ("asbest",              "handhaving"),
    ("asbest",              "verwijdering"),
    ("bodem",               "handhaving"),
    ("afvalstoffen",        "toezicht"),
    ("afvalwater",          "handhaving"),
    ("emissie",             "handhaving"),
    ("meststoffen",         "toezicht"),
    ("biociden",            "toezicht"),
    ("bestrijdingsmiddelen", "toezicht"),
    ("ozonlaag",            "toezicht"),
    ("fluorhoudende gassen", "toezicht"),
    ("energielabel",        "toezicht"),
    # Bouw & Producten
    ("bouwproducten",       "toezicht"),
    ("CE-markering",        "toezicht"),
    ("drinkwater",          "toezicht"),
    ("drinkwater",          "handhaving"),
]

# ===========================================================================
# Gecombineerde lijsten per modus
# ===========================================================================
ALL_SEARCH_TERMS_SIMPLE = SEARCH_TERMS_ILT + SEARCH_TERMS_MINISTERIES

# Alle modi (voor --terms keuze in CLI)
TERM_CATEGORY_SIMPLE = {
    "ILT":        SEARCH_TERMS_ILT,
    "MINISTERIES": SEARCH_TERMS_MINISTERIES,
    "ILT+MIN":    ALL_SEARCH_TERMS_SIMPLE,
}

# ===========================================================================
# ILT Toezichtdomeinen — voor classificatie achteraf
# ===========================================================================
ILT_DOMAINS = {
    "luchtvaart": {
        "keywords": [
            "luchtvaart", "luchtvaartuig", "luchtvaartmaatschappij",
            "vliegtuig", "luchthaven", "burgerluchthaven",
            "luchtruim", "EASA", "ICAO", "rijksluchtvaartdienst",
        ],
        "label": "Luchtvaart",
    },
    "scheepvaart": {
        "keywords": [
            "scheepvaart", "schip", "vaartuig", "haven", "zeevaart",
            "binnenvaart", "zeeschip", "binnenvaartschip",
            "SOLAS", "MARPOL", "IMO",
        ],
        "label": "Scheepvaart",
    },
    "rail": {
        "keywords": [
            "spoorweg", "spoorwegen", "spoor", "trein", "rail",
            "lokaal spoor", "tram", "metro", "ERA",
        ],
        "label": "Rail",
    },
    "wegvervoer": {
        "keywords": [
            "wegvervoer", "vrachtwagen", "autobus", "taxivervoer",
            "rijtijden", "wegvoertuig", "tachograaf", "cabotage",
            "transporteur",
        ],
        "label": "Wegvervoer",
    },
    "gevaarlijke_stoffen": {
        "keywords": [
            "gevaarlijke stoffen", "BRZO", "RIE", "Seveso",
            "explosief", "explosieve stof", "ADR", "RID", "ADN",
            "vuurwerk", "pyrotechnisch",
        ],
        "label": "Gevaarlijke stoffen",
    },
    "milieu_leefomgeving": {
        "keywords": [
            "milieu", "omgeving", "bodem", "lucht", "geluid",
            "afval", "afvalstoffen", "afvalwater",
            "meststof", "meststoffen", "biociden",
            "bestrijdingsmiddelen", "gewasbeschermingsmiddel",
            "asbest", "energie", "emissie", "fluorhoudende",
            "ozonlaag", "klimaat",
        ],
        "label": "Milieu & Leefomgeving",
    },
    "bouw_producten": {
        "keywords": [
            "bouwproduct", "bouwproducten", "CE-markering",
            "bouwstof", "drinkwater", "energielabel",
        ],
        "label": "Bouw & Producten",
    },
}

# ===========================================================================
# Taaktypes — voor classificatie achteraf
# ===========================================================================
TASK_TYPES = {
    "toezicht":     ["toezicht", "inspectie", "controle", "surveillance"],
    "handhaving":   ["handhaving", "bestuursdwang", "dwangsom", "boete",
                     "opleggen", "intrekking"],
    "vergunning":   ["vergunning", "ontheffing", "erkenning",
                     "goedkeuring", "registratie"],
    "certificering": ["certificering", "certificaat", "keurmerken",
                      "typekeuring", "keuring"],
    "advies":       ["advies", "aanbeveling", "signalering"],
}

# ===========================================================================
# Output bestanden
# ===========================================================================
OUTPUT_CSV   = "data/results/ilt_regelgeving_inventarisatie.csv"
OUTPUT_EXCEL = "data/results/ilt_regelgeving_inventarisatie.xlsx"
OUTPUT_GAPS  = "data/results/ilt_manco_analyse.csv"
