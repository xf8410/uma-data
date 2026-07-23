#!/usr/bin/env python3
"""Build a scenario-neutral support-card simulator catalog from master.mdb.

Mechanics and all raw numeric values come from master.mdb only; no external
simulator/wiki data is used. Chinese display names (display_name_zh) and
effect categories are manual in-project metadata, NOT MDB-native fields.

Per-card output sections are strictly separated:
- uncap_profiles / level_breakpoints: normal effects from
  support_card_effect_table (B bonuses keep stable machine keys and carry
  category/target/display_name_zh metadata);
- unique_effect: direct and complex unique effects from
  support_card_unique_effect (raw parameters always retained; formulas that
  are not confirmed from uma-data sources are evaluation_status="unknown");
- hint_effects: skill hints and hint-event parameter rewards from
  single_mode_hint_gain. Hint-event rewards NEVER enter the B-bonus fields;
- resolved_effects_when_condition_met: merged view for bond-threshold unique
  effects (type 101), with normal/unique sources kept separate;
- card_specific_runtime: raw runtime fields whose meaning is unknown;
- group_members: raw support_card_group membership rows (group cards only).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

try:
    from unique_effect_decoder import (
        DIRECT_EFFECT_KEYS, EFFECT_METADATA, STAT_TARGETS, decode_unique_slot,
        effect_metadata,
    )
except ModuleNotFoundError:
    from support_card_model.unique_effect_decoder import (
        DIRECT_EFFECT_KEYS, EFFECT_METADATA, STAT_TARGETS, decode_unique_slot,
        effect_metadata,
    )

LEVEL_COLUMNS = [(1, "init"), (5, "limit_lv5"), (10, "limit_lv10"),
                 (15, "limit_lv15"), (20, "limit_lv20"), (25, "limit_lv25"),
                 (30, "limit_lv30"), (35, "limit_lv35"), (40, "limit_lv40"),
                 (45, "limit_lv45"), (50, "limit_lv50")]

EFFECT_KEYS = {effect_type: key for effect_type, key in DIRECT_EFFECT_KEYS.items()
               if effect_type <= 32}

COMMAND_NAMES = {101: "speed", 105: "stamina", 102: "power", 103: "guts", 106: "wit"}
CARD_TYPE_NAMES = {1: "training", 2: "friend", 3: "group"}
RARITY_NAMES = {1: "R", 2: "SR", 3: "SSR"}

HINT_REWARD_TARGET_ZH = {
    1: "Hint事件速度奖励", 2: "Hint事件耐力奖励", 3: "Hint事件力量奖励",
    4: "Hint事件根性奖励", 5: "Hint事件智力奖励", 30: "Hint事件技能Pt奖励",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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


def unique_effect(row: Mapping[str, Any] | None, description_ja: str = "") -> Dict[str, Any] | None:
    if row is None:
        return None
    slots = []
    for index in (0, 1):
        effect_type = int(row[f"type_{index}"])
        if effect_type == 0:
            continue
        values = [int(row[f"value_{index}"])] + [int(row[f"value_{index}_{n}"]) for n in range(1, 5)]
        slot = decode_unique_slot(effect_type, values)
        slot["type"] = effect_type
        slot["values"] = values
        slots.append(slot)
    return {
        "id": int(row["id"]), "lv_raw": int(row["lv"]),
        "slots": slots, "idle_mode_sub_rate": int(row["idle_mode_sub_rate"]),
        "description_ja": description_ja,
        "raw": {key: int(value) for key, value in row.items()},
    }


# Safety whitelist for the merged conditional view: only nested effects that
# are direct, MDB-confirmed effect types may be merged. Anything else (unknown
# semantics or runtime actions) keeps the slot unresolved.
SAFE_RESOLVED_NESTED_TYPES = frozenset(DIRECT_EFFECT_KEYS)


def resolved_when_condition_met(normal: Mapping[str, Any],
                                unique: Dict[str, Any] | None) -> Dict[str, Any] | None:
    """Merged view for bond-threshold (type 101) unique effects.

    Normal and unique sources are kept separate, then merged. Type-41
    all_stat_bonus is expanded into the five B-bonus keys exactly once at
    this single documented expansion point; the raw all_stat_bonus key is
    not carried into the merged totals.

    The merged values are CONDITIONAL: they apply only when the condition is
    met. The default card panel remains the normal (unconditional) effects.
    """
    if not unique:
        return None
    slots = [slot for slot in unique["slots"]
             if slot.get("type") == 101 and slot.get("evaluation_status") == "numerically_evaluable"]
    if not slots:
        return None
    # Collect ALL safely mergeable type-101 slots first; never return after
    # the first one. Multiple slots are only merged when they share the exact
    # same condition; distinct conditions cannot be represented losslessly in
    # this single-object view and must stay unresolved.
    conditions = {json.dumps(slot.get("condition", {}), sort_keys=True) for slot in slots}
    condition = dict(slots[0].get("condition", {}))
    if len(conditions) != 1:
        return {"resolution_status": "unresolved",
                "unresolved_reason": "multiple_distinct_conditions_not_representable",
                "conditions": [dict(slot.get("condition", {})) for slot in slots]}
    for slot in slots:
        nested_types = [effect["effect_type"] for effect in slot.get("effects", [])]
        if not all(effect_type in SAFE_RESOLVED_NESTED_TYPES for effect_type in nested_types):
            return {"condition": condition,
                    "resolution_status": "unresolved",
                    "unresolved_reason": "nested_effect_outside_direct_whitelist"}
    unique_contrib: Dict[str, int] = {}
    expanded = False
    for slot in slots:
        for effect in slot.get("effects", []):
            if effect["effect_type"] == 41:
                expanded = True
                for stat in STAT_TARGETS:
                    key = f"{stat}_bonus"
                    unique_contrib[key] = unique_contrib.get(key, 0) + int(effect["value"])
            else:
                key = effect["effect_key"]
                unique_contrib[key] = unique_contrib.get(key, 0) + int(effect["value"])
    merged = dict(normal)
    for key, value in unique_contrib.items():
        merged[key] = merged.get(key, 0) + value
    return {"condition": condition,
            "view_kind": "static_conditional_merge_not_runtime_evaluation",
            "resolution_status": "resolved",
            "condition_status": "conditional_not_passive",
            "merged_slot_count": len(slots),
            "effects": merged,
            "sources": {"normal": dict(normal), "unique": unique_contrib},
            "all_stat_bonus_expanded_in_resolved": expanded,
            "default_panel_effects": dict(normal),
            "consumer_warning": "effects apply only when the condition is met; "
                                "the unconditional card panel is default_panel_effects."}


def hint_effects(rows: list[Mapping[str, Any]]) -> Dict[str, Any]:
    skill_rows = []
    normal_param_rows = []
    conditional_param_rows = []
    for row in rows:
        entry = {key: int(row[key]) for key in (
            "id", "hint_id", "support_card_id", "hint_group", "hint_gain_type",
            "hint_value_1", "hint_value_2", "group_id", "condition_set_id", "priority")}
        if entry["hint_gain_type"] == 0:
            # hint_value_1 matches skill_data.id; hint_value_2 is the hint level.
            entry["semantics"] = "skill_hint"
            skill_rows.append(entry)
        else:
            entry["effect_category"] = "hint_event_reward"
            entry["display_name_zh"] = HINT_REWARD_TARGET_ZH.get(
                entry["hint_value_1"], f"Hint事件未知奖励(raw_{entry['hint_value_1']})")
            if entry["condition_set_id"]:
                conditional_param_rows.append(entry)
            else:
                normal_param_rows.append(entry)
    return {
        "skill_hint_rows": skill_rows,
        "hint_event_parameter_rewards": {
            "normal_parameter_reward_rows": normal_param_rows,
            "conditional_parameter_reward_rows": conditional_param_rows,
            # Priority/override algorithm between rows (e.g. priority 100 vs
            # 90) is not confirmed from uma-data sources.
            "selection_semantics": "unknown",
        },
    }


def build_catalog(database: Path) -> Dict[str, Any]:
    connection = sqlite3.connect(str(database))
    connection.row_factory = sqlite3.Row
    effect_names = {int(row["index"]): row["text"] for row in connection.execute(
        'SELECT "index", text FROM text_data WHERE category=151')}
    effect_descriptions = {int(row["index"]): row["text"] for row in connection.execute(
        'SELECT "index", text FROM text_data WHERE category=154')}
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
    unique_descriptions = {int(row["index"]): row["text"] for row in connection.execute(
        'SELECT "index", text FROM text_data WHERE category=155')}
    effect_rows: Dict[int, list[Dict[str, Any]]] = {}
    for row in connection.execute("SELECT * FROM support_card_effect_table ORDER BY id, type"):
        effect_rows.setdefault(int(row["id"]), []).append(dict(row))
    hint_rows: Dict[int, list[Dict[str, Any]]] = {}
    for row in connection.execute("SELECT * FROM single_mode_hint_gain ORDER BY id"):
        hint_rows.setdefault(int(row["support_card_id"]), []).append(dict(row))
    group_members: Dict[int, list[Dict[str, Any]]] = {}
    for row in connection.execute("SELECT * FROM support_card_group ORDER BY id"):
        group_members.setdefault(int(row["support_card_id"]), []).append(
            {"chara_id": int(row["chara_id"]), "outing_max": int(row["outing_max"])})

    cards = []
    for card in connection.execute("SELECT * FROM support_card_data ORDER BY id"):
        card = dict(card)
        card_id, rarity = int(card["id"]), int(card["rarity"])
        table_rows = effect_rows.get(int(card["effect_table_id"]), [])
        profiles = []
        for uncap, max_level in enumerate(limits[rarity]):
            profile = {"uncap": uncap, "max_level": max_level}
            profile.update(resolved_effects(table_rows, max_level))
            profiles.append(profile)
        breakpoints = []
        max_level = limits[rarity][-1]
        for level, _ in LEVEL_COLUMNS:
            if level <= max_level:
                state = {"level": level}
                state.update(resolved_effects(table_rows, level))
                breakpoints.append(state)
        unique = unique_effect(unique_rows.get(int(card["unique_effect_id"])),
                               unique_descriptions.get(int(card["unique_effect_id"]), ""))
        entry: Dict[str, Any] = {
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
            "unique_effect": unique,
            "hint_effects": hint_effects(hint_rows.get(card_id, [])),
            "resolved_effects_when_condition_met": resolved_when_condition_met(
                profiles[-1]["effects"], unique),
        }
        if int(card["effect_id"]) != 0:
            entry["card_specific_runtime"] = {
                "effect_id_raw": int(card["effect_id"]),
                "interpretation": "unknown"}
        if card_id in group_members:
            entry["group_members"] = group_members[card_id]
        cards.append(entry)
    connection.close()
    return {
        "schema_version": 2, "domain": "scenario_neutral_support_card_model",
        "source": {"file": database.name, "sha256": sha256(database),
                   "tables": ["support_card_data", "support_card_effect_table",
                              "support_card_unique_effect", "support_card_limit",
                              "support_card_group", "single_mode_hint_gain", "text_data"]},
        "effect_types": {str(effect_type): {"key": DIRECT_EFFECT_KEYS[effect_type],
                                            "name_ja": effect_names.get(effect_type, ""),
                                            "description_ja": effect_descriptions.get(effect_type, ""),
                                            **effect_metadata(effect_type)}
                         for effect_type in sorted(DIRECT_EFFECT_KEYS)},
        "resolution_rules": {
            "normal_effect": "At a requested level, use the latest non-negative init/limit_lvN value whose N is not greater than the level.",
            "uncap_profile": "uncap 0..4 uses support_card_limit.limit_0..limit_4 as max_level.",
            "unique_effect": "Direct types are confirmed MDB effects. Complex types 101..122 keep raw parameters and the category-155 official description; only slots whose evaluation is a direct restatement of raw fields produce numbers, everything else is evaluation_status=unknown and is never evaluated to 0.",
            "all_stat_bonus_expansion": "Type 41 keeps its raw all_stat_bonus entry plus a read-only expanded_stat_bonuses view. Evaluators apply either the raw entry or the expansion, never both. The single documented expansion point is resolved_effects_when_condition_met.",
            "resolved_when_condition_met": "Generated only for type-101 slots whose nested effects all belong to the direct-effect whitelist; the merged effects are conditional (condition_status=conditional_not_passive) and must not be treated as passive panel values.",
            "hint_event_rewards": "single_mode_hint_gain hint_gain_type=1 rows are Hint-event parameter rewards. They never enter the B-bonus (training_stat_bonus) fields. Row selection semantics (priority/override) are unknown.",
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
