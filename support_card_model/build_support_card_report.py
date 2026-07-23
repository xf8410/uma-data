#!/usr/bin/env python3
"""Build an auditable per-card effect report from the simulator catalog.

Sections per card are strictly separated (normal / unique / hint-event
rewards / resolved-conditional view). The report never claims full
resolution: every card carries an explicit evaluation summary and unknown
items stay unknown.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict

COVERAGE_MATRIX = {
    "support_card_events": {
        "coverage": "unknown",
        "detail": "归属链（支援卡→事件→选项奖励）及执行公式均未从 uma-data 证据确认；single_mode_event_choice_reward / single_mode_event_conclusion / single_mode_event_production / single_mode_event_cr_priority 未并入逐卡效果。仓库中的外部抓取事件文件不作为机制证据。",
    },
    "support_card_group": {
        "coverage": "raw_membership_only",
        "detail": "仅覆盖 support_card_group 的成员原始关系（chara_id, outing_max）。",
    },
    "friend_and_group_card_behaviors": {
        "coverage": "unknown",
        "detail": "友人/团队卡的点击、出行、固定事件、训练行为均未确认。",
    },
    "support_card_team_score_bonus": {
        "coverage": "raw_only",
        "detail": "表存在（15 行），未做语义解释。",
    },
    "card_specific_effect_id": {
        "coverage": "raw_only",
        "detail": "5 张团队卡的 support_card_data.effect_id 非零（100-104），保存为 card_specific_runtime.effect_id_raw，解释 unknown。",
    },
    "scenario_specific_effects": {
        "coverage": "excluded",
        "detail": "剧本专属效果不并入通用逐卡训练效果。",
    },
}


def build_report(catalog: Dict[str, Any]) -> Dict[str, Any]:
    cards = []
    normal_types = Counter()
    unique_types = Counter()
    hint_reward_cards = 0
    conditional_hint_rows = 0
    unknown_unique_slots = []
    structurally_decoded_slots = 0
    numerically_evaluable_slots = 0
    action_only_slots = 0
    action_only_type_distribution = Counter()
    non_empty_slots = 0
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
                slots.append({key: value for key, value in slot.items() if key != "values"})
                non_empty_slots += 1
                status = slot.get("evaluation_status", "unknown")
                if status in ("numerically_evaluable", "action_only_not_numerically_evaluable"):
                    structurally_decoded_slots += 1
                if status == "numerically_evaluable":
                    numerically_evaluable_slots += 1
                if status == "action_only_not_numerically_evaluable":
                    action_only_slots += 1
                    action_only_type_distribution[str(slot["type"])] += 1
                if status == "unknown":
                    unknown_unique_slots.append({
                        "support_card_id": card["support_card_id"],
                        "type": slot["type"],
                        "evaluation_status": slot.get("evaluation_status", "unknown"),
                        "unresolved_reason": slot.get("unresolved_reason", ""),
                    })
            unique_summary = {
                "description_ja": unique.get("description_ja", ""),
                "slots": slots,
                "raw": unique["raw"],
            }
        rewards = card["hint_effects"]["hint_event_parameter_rewards"]
        if rewards["normal_parameter_reward_rows"] or rewards["conditional_parameter_reward_rows"]:
            hint_reward_cards += 1
        conditional_hint_rows += len(rewards["conditional_parameter_reward_rows"])
        entry = {
            "support_card_id": card["support_card_id"], "name_ja": card["name_ja"],
            "chara_id": card["chara_id"], "chara_name_ja": card["chara_name_ja"],
            "rarity_name": card["rarity_name"],
            "support_card_type": card["support_card_type_name"],
            "training_type": card["training_type"],
            "normal_effect_profiles": profiles,
            "level_breakpoints": card["level_breakpoints"],
            "unique_effect": unique_summary,
            "hint_effects": card["hint_effects"],
            "resolved_effects_when_condition_met": card.get("resolved_effects_when_condition_met"),
        }
        if "card_specific_runtime" in card:
            entry["card_specific_runtime"] = card["card_specific_runtime"]
        if "group_members" in card:
            entry["group_members"] = card["group_members"]
        cards.append(entry)
    return {
        "schema_version": 2, "domain": "per_card_effect_audit",
        "source_catalog_schema_version": catalog["schema_version"],
        "card_count": len(cards),
        "coverage": {
            "cards_with_normal_effect_table": len(cards),
            "cards_with_unique_effect": sum(card["unique_effect"] is not None for card in cards),
            "cards_without_unique_effect": sum(card["unique_effect"] is None for card in cards),
            "normal_effect_occurrences_by_key": dict(sorted(normal_types.items())),
            "unique_slot_occurrences_by_type": dict(sorted(unique_types.items(), key=lambda row: int(row[0]))),
            "unique_slot_evaluation": {
                "non_empty_slots": non_empty_slots,
                "structurally_decoded_slots": structurally_decoded_slots,
                "numerically_evaluable_slots": numerically_evaluable_slots,
                "action_only_not_numerically_evaluable_slots": action_only_slots,
                "action_only_type_distribution": dict(sorted(action_only_type_distribution.items(), key=lambda row: int(row[0]))),
                "unknown_formula_slots": len(unknown_unique_slots),
                "unknown_detail": unknown_unique_slots,
                "definitions": {
                    "structurally_decoded": "可以安全描述结构或动作，不一定可计算最终结果。",
                    "numerically_evaluable": "MDB 条件与直接值可生成静态数值结果（含 type 115 这类数值经 actions 携带、目标/时机由 category 155 文本确认的槽位）；不代表完整训练公式、叠加顺序、取整或剧本倍率已确认。",
                    "action_only_not_numerically_evaluable": "动作结构已知，但概率/时机/抽选过程未知，不做随机求值、不产出数值属性效果。",
                    "unknown_formula": "结构可能已知，但精确数值求值未确认；仅保留 MDB 原始参数与官方文本，不求值、不得视为 0。",
                },
                "note": "non_empty_slots = structurally_decoded_slots + unknown_formula_slots；structurally_decoded_slots = numerically_evaluable_slots + action_only_not_numerically_evaluable_slots。",
            },
            "hint_event_rewards": {
                "cards_with_parameter_reward_rows": hint_reward_cards,
                "conditional_parameter_reward_rows_total": conditional_hint_rows,
                "selection_semantics": "unknown",
            },
            "coverage_matrix": COVERAGE_MATRIX,
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
