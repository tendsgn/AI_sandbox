"""
Diagnostisch script: test de KOOP SRU API voordat de volledige inventarisatie
wordt gestart.

Gebruik:
    python diagnose.py

Wat wordt getest:
  1. Verbinding met zoekservice.overheid.nl
  2. Aantal resultaten voor een eenvoudige authority-query (IenW)
  3. Parsing van het eerste record
  4. Ruwe XML (eerste 3000 tekens) voor handmatige inspectie
"""

import json
import sys
from src.search import diagnose

TEST_QUERY = 'overheid.authority = "Infrastructuur en Waterstaat"'

print(f"API-test: {TEST_QUERY}\n")
print("-" * 60)

try:
    result = diagnose(TEST_QUERY)
except Exception as exc:
    print(f"FOUT: kon API niet bereiken — {exc}")
    sys.exit(1)

print(f"HTTP-status:     {result['status_code']}")
print(f"Totaal records:  {result['total_results']}")
print()

if result["first_record"]:
    print("Eerste geparsed record:")
    print(json.dumps(result["first_record"], indent=2, ensure_ascii=False))
else:
    print("Geen records geparsed (mogelijk XML-structuur afwijkend).")

print()
print("Ruwe XML (eerste 3000 tekens):")
print("-" * 60)
print(result["raw_xml_snippet"])
