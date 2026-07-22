#!/usr/bin/env python3
"""Build a scenario-neutral support-card simulator catalog from master.mdb."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

try:
    from unique_effect_decoder import decode_unique_slot
except ModuleNotFoundError:
    from support_card_model.unique_effect_decoder import decode_unique_slot

LEVEL_COLUMNS = [(1, "init"), (5, "limit_lv5"), (10, "limit_lv10"),
                 (15, "limit_lv15"), (20, "limit_lv20"), (25, "limit_lv25"),
                 (30, "limit_lv30"), (35, "limit_lv35"), (40, "limit_lv40"),
                 (45, "limit_lv45"), (50, "limit_lv50")]

EFFECT_KEYS = {
    1: "friendship_bonus", 2: "motivation_bonus", 3: "speed_bonus",
    4: "stamina_bonus", 5: "power_bonus", 6: "guts_bonus", 7: "wit_bonus",
    8: "training_bonus", 9: "initial_speed", 10: "initial_stamina",
    11: "initial_power", 12: "initial_guts", 13: "initial_wit",
    14: "initial_bond", 15: "race_bonus", 16: "fan_bonus",
    17: "hint_level", 18: "hint_rate", 19: "specialty_rate",
    20: "speed_limit", 21: "stamina_limit", 22: "power_limit",
    23: "guts_limit", 24: "wit_limit", 25: "event_recovery",
    26: "event_effect", 27: "failure_rate_drop", 28: "vital_cost_drop",
    29: "minigame_effect", 30: "skill_pt_bonus", 31: "wit_recovery",
    32: "initial_skill_pt",
}

COMMAND_NAMES = {101: "speed", 105: "stamina", 102: "power", 103: "guts", 106: "wit"}
CARD_TYPE_NAMES = {1: "training", 2: "friend", 3: "group"}
RARITY_NAMES = {1: "R", 2: "SR", 3: "SSR"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rows(connection: sqlite3.Connection, query: str, args: Iterable[Any] = ()):
    return [dict(row) for row in connection.execute(query, tuple(args))]


def resolved_effects(effect_rows: list[Mapping[str, Any]], level: int) -> Dict[str, Any]:
    resolved: Dict[str, Any] = {}
    raw: Dict[str, Any] = {}
    for row in effect_rows:
        value = None
        for threshold, column in LEVEL_COLUMNS:
            candidate = int(row[column])
            if threshold <= level and candidate >= 0:
                value = candidate
        if value is None:
            continue
        effect_type = int(row["type"])
        key = EFFECT_KEYS.get(effect_type)
        if key is None:
            raw[str(effect_type)] = value
        else:
            resolved[key] = value
    result: Dict[str, Any] = {"effects": resolved}
    if raw:
        result["unknown_effects_raw"] = raw
    return result


def unique_effect(row: Mapping[str, Any] | None) -> Dict[str, Any] | None:
    if row is None:
        return None
    slots = []
    fully_resolved = True
    for index in (0, 1):
        effect_type = int(row[f"type_{index}"])
        if effect_type == 0:
            continue
        values = [int(row[f"value_{index}"])] + [int(row[f"value_{index}_{n}"]) for n in range(1, 5)]
        slot = decode_unique_slot(effect_type, values)
        slot["type"] = effect_type
        slot["values"] = values
        if slot.get("status") not in ("decoded",):
            fully_resolved = False
        slots.append(slot)
    return {
        "id": int(row["id"]), "lv_raw": int(row["lv"]),
        "slots": slots, "idle_mode_sub_rate": int(row["idle_mode_sub_rate"]),
        "fully_resolved": fully_resolved,
        "raw": {key: int(value) for key, value in row.items()},
    }


def build_catalog(database: Path) -> Dict[str, Any]:
    connection = sqlite3.connect(str(database))
    connection.row_factory = sqlite3.Row
    effect_names = {int(row["index"]): row["text"] for row in connection.execute(
        'SELECT "index", text FROM text_data WHERE category=151')}
    limits = {int(row["rarity"]): [int(row[f"limit_{i}"]) for i in range(5)]
              for row in connection.execute("SELECT * FROM support_card_limit")}
    names = {int(row["index"]): row["text"] for row in connection.execute(
        'SELECT "index", text FROM text_data WHERE category=75')}
    titles = {int(row["index"]): row["text"] for row in connection.execute(
        'SELECT "index", text FROM text_data WHERE category=76')}
    chara_names = {int(row["index"]): row["text"] for row in connection.execute(
        'SELECT "index", text FROM text_data WHERE category=77')}
    unique_rows = {int(row["id"]): dict(row) for row in connection.execute(
        "SELECT * FROM support_card_unique_effect")}
    effect_rows: Dict[int, list[Dict[str, Any]]] = {}
    for row in connection.execute("SELECT * FROM support_card_effect_table ORDER BY id, type"):
        effect_rows.setdefault(int(row["id"]), []).append(dict(row))

    cards = []
    for card in connection.execute("SELECT * FROM support_card_data ORDER BY id"):
        card = dict(card)
        card_id, rarity = int(card["id"]), int(card["rarity"])
        profiles = []
        for uncap, max_level in enumerate(limits[rarity]):
            profile = {"uncap": uncap, "max_level": max_level}
            profile.update(resolved_effects(effect_rows.get(int(card["effect_table_id"]), []), max_level))
            profiles.append(profile)
        breakpoints = []
        max_level = limits[rarity][-1]
        for level, _ in LEVEL_COLUMNS:
            if level <= max_level:
                state = {"level": level}
                state.update(resolved_effects(effect_rows.get(int(card["effect_table_id"]), []), level))
                breakpoints.append(state)
        cards.append({
            "support_card_id": card_id,
            "name_ja": names.get(card_id, ""), "title_ja": titles.get(card_id, ""),
            "chara_name_ja": chara_names.get(card_id, ""), "chara_id": int(card["chara_id"]),
            "rarity": rarity, "rarity_name": RARITY_NAMES.get(rarity, str(rarity)),
            "support_card_type": int(card["support_card_type"]),
            "support_card_type_name": CARD_TYPE_NAMES.get(int(card["support_card_type"]), "unknown"),
            "command_type": int(card["command_type"]), "command_id": int(card["command_id"]),
            "training_type": COMMAND_NAMES.get(int(card["command_id"])),
            "outing_max": int(card["outing_max"]), "skill_set_id": int(card["skill_set_id"]),
            "effect_table_id": int(card["effect_table_id"]),
            "unique_effect_id": int(card["unique_effect_id"]),
            "uncap_profiles": profiles, "level_breakpoints": breakpoints,
            "unique_effect": unique_effect(unique_rows.get(int(card["unique_effect_id"]))),
        })
    connection.close()
    return {
        "schema_version": 1, "domain": "scenario_neutral_support_card_model",
        "source": {"file": database.name, "sha256": sha256(database),
                   "tables": ["support_card_data", "support_card_effect_table",
                              "support_card_unique_effect", "support_card_limit", "text_data"]},
        "effect_types": {str(effect_type): {"key": key, "name_ja": effect_names.get(effect_type, "")}
                         for effect_type, key in EFFECT_KEYS.items()},
        "resolution_rules": {
            "normal_effect": "At a requested level, use the latest non-negative init/limit_lvN value whose N is not greater than the level.",
            "uncap_profile": "uncap 0..4 uses support_card_limit.limit_0..limit_4 as max_level.",
            "unique_effect": "Types 1..32 are direct effects. Complex types 101..122 are decoded into machine-readable conditions/formulas/actions; raw fields are always retained. Type 107 remains candidate_formula because the cross-checking implementation marks its data interpretation TODO."
        },
        "card_count": len(cards), "cards": cards,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    args = parser.parse_args()
    catalog = build_catalog(args.database)
    args.output.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
