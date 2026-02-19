# ILT Wet- en Regelgeving Inventarisatie

Systematische inventarisatie van alle geldende Nederlandse wet- en regelgeving
waarbij **ILT (Inspectie Leefomgeving en Transport)** een taak is toebedeeld.

## Doel

ILT's eigen Jaarplan en Jaarverslag zijn geen volledige bronnen. Dit project zoekt
*vanuit de wetgeving zelf* welke taken aan ILT zijn toebedeeld, en identificeert
**manco's**: taken die formeel bestaan maar niet zichtbaar worden opgepakt.

## Aanpak

```
wetten.overheid.nl (BWB/SRU API)
        │
        ▼
 Zoeken op ILT-namen + historische ministeries + toezichtsconstructies
        │
        ▼
 Filteren: alleen status = 'geldend'
        │
        ▼
 Deduplicatie + classificatie (domein, taaktype)
        │
        ▼
 Manco-analyse vs. ILT-referentie
        │
        ▼
 CSV + Excel output
```

## Projectstructuur

```
.
├── main.py                          # Hoofdscript
├── requirements.txt
├── src/
│   ├── config.py                    # Zoektermen, domeinen, taaktypes
│   ├── search.py                    # SRU API client (wetten.overheid.nl)
│   ├── classifier.py                # Domein- en taaktype-classificatie
│   ├── deduplicator.py              # Deduplicatie op BWB-ID
│   ├── gap_analysis.py              # Manco-analyse
│   └── output.py                    # CSV + Excel export
└── data/
    ├── reference/
    │   └── ilt_bekend_regelgeving.csv   # Handmatig bij te houden referentie
    └── results/                         # Gegenereerde output (gitignore)
```

## Installatie

```bash
pip install -r requirements.txt
```

## Gebruik

```bash
# Volledige run (alle zoektermen)
python main.py

# Alleen ILT-directe zoektermen
python main.py --terms ILT

# Snelle test met één zoekterm
python main.py --dry-run

# Alleen CSV, geen Excel
python main.py --no-excel
```

## Output

| Bestand | Inhoud |
|---------|--------|
| `data/results/ilt_regelgeving_inventarisatie.csv` | Alle gevonden regelgeving + classificatie |
| `data/results/ilt_manco_analyse.csv` | Alleen de manco's (niet-gedekte taken) |
| `data/results/ilt_regelgeving_inventarisatie.xlsx` | Excel met twee tabs: inventarisatie + manco's |
| `data/results/run.log` | Logbestand van de laatste run |

## Manco-categorieën

| Categorie | Betekenis |
|-----------|-----------|
| `gedekt` | Wet is aanwezig in ILT-referentie |
| `ongedekte_taak` | Wet wijst toezichttaak toe maar niet zichtbaar in ILT-publicaties |
| `slapende_bevoegdheid` | ILT is bevoegd maar geen actief programma aantoonbaar |
| `verouderde_wettekst` | Wet noemt voorgangersministerie; opvolging door ILT onduidelijk |

## Referentiebestand bijhouden

Voeg bekende ILT-regelgeving toe aan `data/reference/ilt_bekend_regelgeving.csv`:

```csv
bwb_id,titel,bron,toelichting
BWBR0005629,Wet luchtvaart,jaarplan,Kernwet luchtvaarttoezicht ILT
```

Kolom `bron`: gebruik `jaarplan`, `jaarverslag`, `website`, of `handmatig`.

## ILT Toezichtdomeinen

- Luchtvaart
- Scheepvaart
- Rail
- Wegvervoer
- Gevaarlijke stoffen
- Milieu & Leefomgeving
- Bouw & Producten
