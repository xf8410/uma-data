"""Machine-readable decoder/evaluator for support-card unique effects.

Types 101-122 are decoded from MDB category-155 descriptions and cross-checked
against umasim commit 54f3952f8d3a4b14d79ddb3025bce802902295cb. Type 107 keeps
an explicit candidate-formula warning because that implementation also marks its
data interpretation TODO.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping

DIRECT_EFFECT_KEYS = {
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
    32: "initial_skill_pt", 33: "hint_count_bonus", 41: "all_stat_bonus",
}

COMPLEX_UNIQUE_DEFINITIONS = {
    101: {"key": "bond_threshold_effects", "status": "decoded"},
    102: {"key": "bond_threshold_non_specialty_training", "status": "decoded"},
    103: {"key": "deck_type_count_training_bonus", "status": "decoded"},
    104: {"key": "fan_count_training_bonus", "status": "decoded"},
    105: {"key": "deck_composition_initial_stats", "status": "decoded"},
    106: {"key": "friendship_training_count_effect", "status": "decoded"},
    107: {"key": "low_vital_friendship_bonus", "status": "candidate_formula"},
    108: {"key": "max_vital_scaled_effect", "status": "decoded"},
    109: {"key": "total_bond_scaled_effect", "status": "decoded"},
    110: {"key": "training_support_count_effect", "status": "decoded"},
    111: {"key": "training_level_effect", "status": "decoded"},
    112: {"key": "failure_rate_zero_chance", "status": "decoded"},
    113: {"key": "friendship_training_effect", "status": "decoded"},
    114: {"key": "current_vital_scaled_effect", "status": "decoded"},
    115: {"key": "all_cards_initial_effect", "status": "decoded"},
    116: {"key": "owned_skill_count_effect", "status": "decoded"},
    117: {"key": "total_training_level_effect", "status": "decoded"},
    118: {"key": "second_training_position", "status": "decoded"},
    119: {"key": "bond_threshold_position_rate", "status": "decoded"},
    120: {"key": "deck_composition_parameter_bonus", "status": "decoded"},
    121: {"key": "training_bond_gain_bonus", "status": "decoded"},
    122: {"key": "next_turn_other_support_specialty", "status": "decoded"},
}

SKILL_CATEGORY_KEYS = {1: "speed", 2: "acceleration", 3: "recovery"}
STAT_TYPES = ("speed", "stamina", "power", "guts", "wit")


def _effect(effect_type: int, value: int) -> Dict[str, Any]:
    return {"effect_type": effect_type,
            "effect_key": DIRECT_EFFECT_KEYS.get(effect_type, f"raw_{effect_type}"),
            "value": value}


def decode_unique_slot(effect_type: int, values: list[int]) -> Dict[str, Any]:
    v0, v1, v2, v3, v4 = values
    if effect_type in DIRECT_EFFECT_KEYS:
        effect = _effect(effect_type, v0)
        return {"kind": "direct", "status": "decoded", "effect_key": effect["effect_key"],
                "value": v0, "effect": effect}
    definition = COMPLEX_UNIQUE_DEFINITIONS.get(effect_type)
    if definition is None:
        return {"kind": "unknown", "status": "unresolved", "values": values}
    result: Dict[str, Any] = {"kind": "complex", **definition, "parameters": values}
    if effect_type == 101:
        result.update(condition={"bond_at_least": v0}, effects=[_effect(v1, v2), _effect(v3, v4)] if v3 else [_effect(v1, v2)])
    elif effect_type == 102:
        result.update(condition={"bond_at_least": v0, "training_is_not_card_specialty": True}, effects=[_effect(8, v1)])
    elif effect_type == 103:
        result.update(condition={"distinct_deck_types_at_least": v0}, effects=[_effect(8, v1)])
    elif effect_type == 104:
        result.update(effect_type=8, effect_key="training_bonus", formula={"operation": "min", "terms": [v1, {"operation": "floor_div", "terms": ["fan_count", v0]}]})
    elif effect_type == 105:
        result.update(formula={"training_card": {"matching_initial_stat": v0}, "friend_or_group": {"all_initial_stats": v1}})
    elif effect_type == 106:
        result.update(effect_type=v1, effect_key=DIRECT_EFFECT_KEYS.get(v1), formula={"operation": "multiply", "terms": [{"operation": "min", "terms": [v0, "friendship_training_count"]}, v2]})
    elif effect_type == 107:
        result.update(effect_type=v0, effect_key=DIRECT_EFFECT_KEYS.get(v0), formula_status="upstream_reference_marks_interpretation_todo", candidate_formula="15-floor((max(30,current_vital)-30)*15/100)")
    elif effect_type == 108:
        result.update(effect_type=v0, effect_key=DIRECT_EFFECT_KEYS.get(v0), formula=f"min({v4},floor((max_vital-{v1})*{v2}/100+{v3}))")
    elif effect_type == 109:
        result.update(effect_type=v0, effect_key=DIRECT_EFFECT_KEYS.get(v0), formula={"operation": "floor_div", "terms": ["total_deck_bond", v1]})
    elif effect_type == 110:
        result.update(effect_type=v0, effect_key=DIRECT_EFFECT_KEYS.get(v0), formula={"operation": "multiply", "terms": ["training_support_count", v1]})
    elif effect_type == 111:
        result.update(effect_type=v0, effect_key=DIRECT_EFFECT_KEYS.get(v0), formula={"operation": "multiply", "terms": [{"operation": "min", "terms": [5, "training_level"]}, v1]})
    elif effect_type == 112:
        result.update(action="set_failure_rate_zero", probability_percent=v0)
    elif effect_type == 113:
        result.update(condition={"friendship_training": True}, effects=[_effect(v0, v1)])
    elif effect_type == 114:
        result.update(effect_type=v0, effect_key=DIRECT_EFFECT_KEYS.get(v0), formula=f"{v2}-max(0,floor((100-current_vital)/{v1}))")
    elif effect_type == 115:
        result.update(target="all_deck_cards", timing="initial", effects=[_effect(v0, v1)])
    elif effect_type == 116:
        result.update(skill_category=SKILL_CATEGORY_KEYS.get(v0, f"raw_{v0}"), effect_type=v1, effect_key=DIRECT_EFFECT_KEYS.get(v1), formula={"operation": "multiply", "terms": [v2, {"operation": "min", "terms": [f"{SKILL_CATEGORY_KEYS.get(v0, 'raw')}_skill_count", v3]}]})
    elif effect_type == 117:
        result.update(effect_type=v0, effect_key=DIRECT_EFFECT_KEYS.get(v0), formula={"operation": "min", "terms": [v2, "total_training_level"]}, value_1_raw=v1)
    elif effect_type == 118:
        result.update(condition={"bond_at_least": v1}, action="allow_second_training_position", max_positions=2)
    elif effect_type == 119:
        result.update(condition={"bond_at_least": v2}, action="increase_position_rate", value=v0, value_1_raw=v1)
    elif effect_type == 120:
        result.update(condition={"bond_at_least": v1}, formula={"per_matching_deck_card": v2, "per_parameter_cap": v3, "friend_and_group_target": "skill_pt"})
    elif effect_type == 121:
        result.update(action="increase_training_bond_gain", all_participants=v0, additional_if_this_card_present=v1)
    elif effect_type == 122:
        result.update(action="next_turn_effect_for_other_co_training_supports", effects=[_effect(v0, v1)])
    return result


def evaluate_decoded(decoded: Mapping[str, Any], context: Mapping[str, Any]) -> Dict[str, Any]:
    """Evaluate decoded unique effects into additive effects and state actions."""
    if decoded.get("kind") == "direct":
        effect = decoded["effect"]
        return {"effects": {effect["effect_key"]: effect["value"]}, "actions": {}}
    typ = int(context.get("_effect_type", 0))
    p = list(decoded.get("parameters", [0, 0, 0, 0, 0])); v0, v1, v2, v3, v4 = p
    effects: Dict[str, int] = {}; actions: Dict[str, Any] = {}
    def add(t: int, value: int):
        if value:
            key = DIRECT_EFFECT_KEYS.get(t, f"raw_{t}"); effects[key] = effects.get(key, 0) + value
    bond = int(context.get("bond", 0))
    if typ == 101 and bond >= v0:
        add(v1, v2); add(v3, v4)
    elif typ == 102 and bond >= v0 and context.get("training_type") != context.get("card_training_type"): add(8, v1)
    elif typ == 103 and int(context.get("distinct_deck_types", 0)) >= v0: add(8, v1)
    elif typ == 104: add(8, min(v1, int(context.get("fan_count", 0)) // v0))
    elif typ == 105:
        initial = {key: 0 for key in STAT_TYPES}
        for key, count in context.get("deck_counts", {}).items():
            if key in initial: initial[key] += int(count) * v0
            elif key in ("friend", "group"):
                for stat in STAT_TYPES: initial[stat] += int(count) * v1
        actions["initial_stats"] = initial
    elif typ == 106: add(v1, min(v0, int(context.get("friendship_training_count", 0))) * v2)
    elif typ == 107:
        value = 15 - int((max(30, int(context.get("current_vital", 100))) - 30) * 15 / 100)
        add(v0, value); actions["formula_status"] = "candidate"
    elif typ == 108: add(v0, min(v4, int((int(context.get("max_vital", 100)) - v1) * v2 / 100 + v3)))
    elif typ == 109: add(v0, int(context.get("total_deck_bond", 0)) // v1)
    elif typ == 110: add(v0, int(context.get("training_support_count", 0)) * v1)
    elif typ == 111: add(v0, min(5, int(context.get("training_level", 0))) * v1)
    elif typ == 112: actions["failure_rate_zero_chance_percent"] = v0
    elif typ == 113 and context.get("friendship_training"): add(v0, v1)
    elif typ == 114: add(v0, v2 - max(0, (100 - int(context.get("current_vital", 100))) // v1))
    elif typ == 115: actions["all_cards_initial_effect"] = _effect(v0, v1)
    elif typ == 116:
        count = int(context.get("skill_counts", {}).get(SKILL_CATEGORY_KEYS.get(v0), 0)); add(v1, v2 * min(count, v3))
    elif typ == 117: add(v0, min(v2, int(context.get("total_training_level", 0))))
    elif typ == 118: actions["second_training_position"] = bond >= v1
    elif typ == 119 and bond >= v2: actions["position_rate_bonus"] = v0
    elif typ == 120 and bond >= v1:
        counts=context.get("deck_counts", {}); actions["parameter_bonuses"]={stat:min(v3,int(counts.get(stat,0))*v2) for stat in STAT_TYPES}; actions["skill_pt_bonus"] = min(v3,(int(counts.get("friend",0))+int(counts.get("group",0)))*v2)
    elif typ == 121: actions.update(bond_gain_all=v0, bond_gain_if_present=v1)
    elif typ == 122: actions["next_turn_other_support_effect"] = _effect(v0, v1)
    return {"effects": effects, "actions": actions}
