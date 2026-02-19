"""
Configuratie voor de ILT wet- en regelgeving inventarisatie.

Zoekstrategie:
  De KOOP SRU API (zoekservice.overheid.nl) zoekt uitsluitend op metadata,
  niet op inhoud van wetteksten. Daarom zoeken we op:

  Laag 1 — overheid.authority: alle geldende regelgeving waarvoor IenW
            (of een voorgangersministerie) als bevoegd gezag is geregistreerd.
            Dit is de meest directe en volledige methode.

  Laag 2 — keyword: aanvullende zoekslag op metadata-trefwoorden per ILT-domein,
            voor regelgeving die onder een ander ministerie valt maar waarbij
            ILT toezichtstaken uitvoert (bijv. sommige milieuregels).

  De manco-analyse vergelijkt de complete inventarisatie achteraf met ILT-
  publicaties (Jaarplan, Jaarverslag) om niet-gerapporteerde taken zichtbaar
  te maken.
"""

# ===========================================================================
# SRU API (Kennis- en exploitatiecentrum voor officiële overheidspublicaties)
# Documentatie: https://data.overheid.nl/dataset/basis-wetten-bestand
# ===========================================================================
SRU_BASE_URL      = "https://zoekservice.overheid.nl/sru/Search"
SRU_VERSION       = "1.2"
SRU_CONNECTION    = "BWB"
SRU_MAX_RECORDS   = 50       # API-maximum is 50
REQUEST_DELAY_SEC = 1.0      # respectvol crawlen

# Noot: overheidbwb.geldigheidsstatus bestaat NIET als CQL-index (fout 1/16).
# Geldend-filtering vindt post-hoc plaats in search.py op basis van het veld
# overheidbwb:geldigheidsperiode_einddatum uit de XML-response:
#   geldend  ↔  einddatum = "9999-12-31"
#
# Noot: dcterms.type is wel een geldig CQL-index, maar de exacte typewaarden
# zijn "wet", "AMvB", "ministeriele-regeling", "KB" — identiek aan wat de XML
# retourneert. Type-filtering vindt post-hoc plaats in de classifier.

# ===========================================================================
# LAAG 1 — Ministeries als bevoegd gezag (overheid.authority)
#
# Bevraagt alle geldende regelgeving waarbij het genoemde ministerie als
# verantwoordelijk gezag is geregistreerd in het BWB.
# Betreft huidig IenW én historische voorgangers.
# ===========================================================================
AUTHORITY_QUERIES = [
    # Huidig ministerie
    'overheid.authority = "Infrastructuur en Waterstaat"',
    # Voorgangers (regelgeving vaak nog niet geactualiseerd)
    'overheid.authority = "Infrastructuur en Milieu"',
    'overheid.authority = "Verkeer en Waterstaat"',
    'overheid.authority = "Volkshuisvesting, Ruimtelijke Ordening en Milieubeheer"',
    # Co-verantwoordelijkheid: ILT voert ook taken uit onder ander ministerie
    'overheid.authority = "Sociale Zaken en Werkgelegenheid"',     # arbeidsveiligheid
    'overheid.authority = "Economische Zaken en Klimaat"',         # energie, biociden
    'overheid.authority = "Landbouw, Natuur en Voedselkwaliteit"', # meststoffen, gbm
]

# ===========================================================================
# LAAG 2 — Keyword-zoekopdrachten per ILT-domein
#
# Pakt regelgeving op die qua ministry-registratie buiten bovenstaande
# queries valt, maar inhoudelijk wel in een ILT-domein zit.
# 'keyword' is een metadata-gebaseerd veld, geen volledige tekst.
# ===========================================================================
KEYWORD_QUERIES = [
    # Luchtvaart
    'keyword = "luchtvaart"',
    'keyword = "luchthaven"',
    'keyword = "luchtvaartuig"',
    # Scheepvaart
    'keyword = "scheepvaart"',
    'keyword = "zeevaart"',
    'keyword = "binnenvaart"',
    # Rail
    'keyword = "spoorwegen"',
    'keyword = "spoorweg"',
    # Wegvervoer
    'keyword = "wegvervoer"',
    'keyword = "taxivervoer"',
    'keyword = "rijtijden"',
    'keyword = "tachograaf"',
    # Gevaarlijke stoffen
    'keyword = "gevaarlijke stoffen"',
    'keyword = "vuurwerk"',
    'keyword = "explosief"',
    # Milieu & Leefomgeving
    'keyword = "asbest"',
    'keyword = "biociden"',
    'keyword = "bestrijdingsmiddelen"',
    'keyword = "meststoffen"',
    'keyword = "bodemkwaliteit"',
    'keyword = "emissies"',
    # Bouw & Producten
    'keyword = "drinkwater"',
    'keyword = "bouwproducten"',
    'keyword = "energielabel"',
]

# ===========================================================================
# ILT Toezichtdomeinen — voor post-hoc classificatie van gevonden regelgeving
# ===========================================================================
ILT_DOMAINS = {
    "luchtvaart": {
        "keywords": [
            "luchtvaart", "luchtvaartuig", "luchtvaartmaatschappij",
            "vliegtuig", "luchthaven", "burgerluchthaven", "luchtruim",
            "easa", "icao", "rijksluchtvaartdienst",
        ],
        "label": "Luchtvaart",
    },
    "scheepvaart": {
        "keywords": [
            "scheepvaart", "schip", "vaartuig", "haven", "zeevaart",
            "binnenvaart", "zeeschip", "solas", "marpol", "imo",
        ],
        "label": "Scheepvaart",
    },
    "rail": {
        "keywords": [
            "spoorweg", "spoorwegen", "spoor", "trein", "rail",
            "lokaalspoor", "tram", "metro", "era",
        ],
        "label": "Rail",
    },
    "wegvervoer": {
        "keywords": [
            "wegvervoer", "vrachtwagen", "autobus", "taxivervoer",
            "rijtijden", "wegvoertuig", "tachograaf", "cabotage",
        ],
        "label": "Wegvervoer",
    },
    "gevaarlijke_stoffen": {
        "keywords": [
            "gevaarlijke stoffen", "brzo", "rie", "seveso",
            "explosief", "adr", "rid", "adn", "vuurwerk", "pyrotechnisch",
        ],
        "label": "Gevaarlijke stoffen",
    },
    "milieu_leefomgeving": {
        "keywords": [
            "milieu", "bodem", "afval", "afvalstoffen", "afvalwater",
            "meststof", "biociden", "bestrijdingsmiddelen",
            "gewasbeschermingsmiddel", "asbest", "emissie",
            "fluorhoudende", "ozonlaag",
        ],
        "label": "Milieu & Leefomgeving",
    },
    "bouw_producten": {
        "keywords": [
            "bouwproduct", "bouwproducten", "ce-markering",
            "drinkwater", "energielabel",
        ],
        "label": "Bouw & Producten",
    },
}

# ===========================================================================
# Taaktypes — voor classificatie achteraf op basis van titel/citeertitel
# ===========================================================================
TASK_TYPES = {
    "toezicht":      ["toezicht", "inspectie", "controle", "surveillance"],
    "handhaving":    ["handhaving", "bestuursdwang", "dwangsom", "boete",
                      "opleggen", "intrekking"],
    "vergunning":    ["vergunning", "ontheffing", "erkenning",
                      "goedkeuring", "registratie"],
    "certificering": ["certificering", "certificaat", "keurmerken",
                      "typekeuring", "keuring"],
    "advies":        ["advies", "aanbeveling", "signalering"],
}

# ===========================================================================
# Output
# ===========================================================================
OUTPUT_CSV   = "data/results/ilt_regelgeving_inventarisatie.csv"
OUTPUT_EXCEL = "data/results/ilt_regelgeving_inventarisatie.xlsx"
OUTPUT_GAPS  = "data/results/ilt_manco_analyse.csv"
