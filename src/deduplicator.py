"""
Deduplicatie van zoekresultaten.

Dezelfde wet kan gevonden worden via meerdere zoektermen.
We bewaren alle gevonden zoektermen per wet, maar voegen het record samen.
"""

import logging

logger = logging.getLogger(__name__)


def deduplicate(records: list[dict]) -> list[dict]:
    """
    Verwijder dubbele BWB-records. Bij meerdere hits voor dezelfde wet
    worden de gevonden zoektermen gecombineerd.
    """
    seen: dict[str, dict] = {}

    for record in records:
        bwb_id = record.get("bwb_id", "").strip()

        # Fallback: dedup op titel als bwb_id ontbreekt
        key = bwb_id if bwb_id else record.get("titel", "").lower().strip()

        if not key:
            continue

        if key not in seen:
            # Eerste keer: converteer zoekterm naar set
            record["gevonden_op_zoektermen"] = {record.get("gevonden_op_zoekterm", "")}
            seen[key] = record
        else:
            # Al gezien: voeg zoekterm toe aan bestaand record
            seen[key]["gevonden_op_zoektermen"].add(record.get("gevonden_op_zoekterm", ""))

    # Converteer sets naar gesorteerde strings voor export
    result = []
    for record in seen.values():
        zoektermen = sorted(record.pop("gevonden_op_zoektermen", set()))
        record["gevonden_op_zoektermen"] = " | ".join(zoektermen)
        result.append(record)

    logger.info("Na deduplicatie: %d unieke regelingen (was: %d)", len(result), len(records))
    return result
