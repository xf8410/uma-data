#!/usr/bin/env python3
"""Build an auditable per-card effect report from the simulator catalog."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict


def build_report(catalog: Dict[str, Any]) -> Dict[str, Any]:
    cards = []
    normal_types = Counter()
    unique_types = Counter()
    candidate_cards = []
    for card in catalog["cards"]:
        profiles = []
        for profile in card["uncap_profiles"]:
            effects = profile["effects"]
            normal_types.update(effects)
            profiles.append({
                "uncap": profile["uncap"], "max_level": profile["max_level"],
                "effects": effects,
                "unknown_effects_raw": profile.get("unknown_effects_raw", {}),
            })
        unique = card.get("unique_effect")
        unique_summary = None
        if unique:
            slots = []
            for slot in unique["slots"]:
                unique_types[str(slot["type"])] += 1
                slots.append({key: value for key, value in slot.items() if key not in ("values",)})
                if slot.get("status") != "decoded":
                    candidate_cards.append({"support_card_id": card["support_card_id"],
                                            "type": slot["type"], "status": slot.get("status")})
            unique_summary = {
                "description_ja": unique.get("description_ja", ""),
                "fully_resolved": unique["fully_resolved"], "slots": slots,
                "raw": unique["raw"],
            }
        cards.append({
            "support_card_id": card["support_card_id"], "name_ja": card["name_ja"],
            "chara_id": card["chara_id"], "chara_name_ja": card["chara_name_ja"],
            "rarity_name": card["rarity_name"],
            "support_card_type": card["support_card_type_name"],
            "training_type": card["training_type"],
            "normal_effect_profiles": profiles,
            "level_breakpoints": card["level_breakpoints"],
            "unique_effect": unique_summary,
        })
    return {
        "schema_version": 1, "domain": "per_card_effect_audit",
        "source_catalog_schema_version": catalog["schema_version"],
        "card_count": len(cards),
        "coverage": {
            "cards_with_normal_effect_table": len(cards),
            "cards_with_unique_effect": sum(card["unique_effect"] is not None for card in cards),
            "cards_without_unique_effect": sum(card["unique_effect"] is None for card in cards),
            "normal_effect_occurrences_by_key": dict(sorted(normal_types.items())),
            "unique_slot_occurrences_by_type": dict(sorted(unique_types.items(), key=lambda row: int(row[0]))),
            "non_confirmed_unique_slots": candidate_cards,
        },
        "cards": cards,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("catalog", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    args = parser.parse_args()
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    args.output.write_text(json.dumps(build_report(catalog), ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")


if __name__ == "__main__":
    main()
