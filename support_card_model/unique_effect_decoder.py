"""Machine-readable decoder/evaluator for support-card unique effects.

Evidence policy (uma-data only):
- Machine keys are kept stable for existing consumers (speed_bonus etc.).
- Chinese display names and effect categories are attached as metadata.
- Types 1-33/41 are direct MDB effects (confirmed from master.mdb).
- Complex types 101-122 keep ONLY: raw MDB parameters, the category-155
  official description (carried by the extractor), and structure that is a
  direct restatement of raw fields. Exact formulas, probabilities, rounding
  and caps that cannot be confirmed from uma-data sources are reported as
  evaluation_status="unknown" and are NEVER evaluated to a numeric value.
- No external simulator, wiki, or guide-site formula is used.
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

# Category / target / Chinese display-name metadata. Machine keys above are
# unchanged for consumer compatibility; these fields are additive only.
EFFECT_METADATA = {
    1: ("training_bonus_meta", "bond", "友情加成"),
    2: ("training_bonus_meta", "motivation", "干劲效果加成"),
    3: ("training_stat_bonus", "speed", "速度加成"),
    4: ("training_stat_bonus", "stamina", "耐力加成"),
    5: ("training_stat_bonus", "power", "力量加成"),
    6: ("training_stat_bonus", "guts", "根性加成"),
    7: ("training_stat_bonus", "wit", "智力加成"),
    8: ("training_bonus_meta", "training", "训练效果加成"),
    9: ("initial_stat", "speed", "初始速度"),
    10: ("initial_stat", "stamina", "初始耐力"),
    11: ("initial_stat", "power", "初始力量"),
    12: ("initial_stat", "guts", "初始根性"),
    13: ("initial_stat", "wit", "初始智力"),
    14: ("initial_meta", "bond", "初始羁绊"),
    15: ("race_meta", "race_stats", "赛后属性加成"),
    16: ("race_meta", "fans", "粉丝数加成"),
    17: ("hint_meta", "hint_level", "Hint等级加成"),
    18: ("hint_meta", "hint_rate", "Hint发生率加成"),
    19: ("position_meta", "specialty_rate", "擅长训练配置率加成"),
    20: ("limit_meta", "speed", "速度上限加成"),
    21: ("limit_meta", "stamina", "耐力上限加成"),
    22: ("limit_meta", "power", "力量上限加成"),
    23: ("limit_meta", "guts", "根性上限加成"),
    24: ("limit_meta", "wit", "智力上限加成"),
    25: ("event_meta", "recovery", "事件体力恢复加成"),
    26: ("event_meta", "effect", "事件效果量加成"),
    27: ("training_meta", "failure_rate", "训练失败率下降"),
    28: ("training_meta", "vital_cost", "训练体力消耗下降"),
    29: ("minigame_meta", "effect", "小游戏效果加成"),
    30: ("skill_pt_bonus", "skill_pt", "技能Pt加成"),
    31: ("training_meta", "wit_recovery", "智力友情训练恢复加成"),
    32: ("initial_meta", "skill_pt", "初始技能Pt"),
    33: ("hint_meta", "hint_count", "Hint获取数加成"),
    41: ("training_stat_bonus", "all_stats", "全属性加成"),
}

STAT_TARGETS = ("speed", "stamina", "power", "guts", "wit")

# Status vocabulary:
# - structurally_decoded: the slot's structure/action can be safely described
#   from raw MDB fields; it does NOT imply the final result is computable.
# - numerically_evaluable: evaluation is a direct restatement of raw fields
#   and produces numbers under an explicit condition (direct types, and the
#   complex types marked "numeric" below).
# - action_only: structure is known (e.g. type 112 set_failure_rate_zero) but
#   probability/timing are unknown, so no numeric/runtime result is produced.
# - unknown: exact formula not confirmed from uma-data sources.
COMPLEX_UNIQUE_DEFINITIONS = {
    101: {"key": "bond_threshold_effects", "evaluation": "numeric"},
    102: {"key": "bond_threshold_non_specialty_training", "evaluation": "unknown"},
    103: {"key": "deck_type_count_training_bonus", "evaluation": "unknown"},
    104: {"key": "fan_count_training_bonus", "evaluation": "unknown"},
    105: {"key": "deck_composition_initial_stats", "evaluation": "unknown"},
    106: {"key": "friendship_training_count_effect", "evaluation": "unknown"},
    107: {"key": "low_vital_friendship_bonus", "evaluation": "unknown"},
    108: {"key": "max_vital_scaled_effect", "evaluation": "unknown"},
    109: {"key": "total_bond_scaled_effect", "evaluation": "unknown"},
    110: {"key": "training_support_count_effect", "evaluation": "unknown"},
    111: {"key": "training_level_effect", "evaluation": "unknown"},
    112: {"key": "failure_rate_zero_chance", "evaluation": "action_only"},
    113: {"key": "friendship_training_effect", "evaluation": "numeric"},
    114: {"key": "current_vital_scaled_effect", "evaluation": "unknown"},
    115: {"key": "all_cards_initial_effect", "evaluation": "numeric"},
    116: {"key": "owned_skill_count_effect", "evaluation": "unknown"},
    117: {"key": "total_training_level_effect", "evaluation": "unknown"},
    118: {"key": "second_training_position", "evaluation": "action_only"},
    119: {"key": "bond_threshold_position_rate", "evaluation": "unknown"},
    120: {"key": "deck_composition_parameter_bonus", "evaluation": "unknown"},
    121: {"key": "training_bond_gain_bonus", "evaluation": "unknown"},
    122: {"key": "next_turn_other_support_specialty", "evaluation": "unknown"},
}

UNKNOWN_REASON = "exact_formula_not_confirmed_from_uma_data_sources"


def effect_metadata(effect_type: int) -> Dict[str, Any]:
    category, target, display_name_zh = EFFECT_METADATA.get(
        effect_type, ("unknown", f"raw_{effect_type}", "未知效果"))
    return {"effect_category": category, "target": target,
            "display_name_zh": display_name_zh}


def _effect(effect_type: int, value: int) -> Dict[str, Any]:
    effect = {"effect_type": effect_type,
              "effect_key": DIRECT_EFFECT_KEYS.get(effect_type, f"raw_{effect_type}"),
              "value": value}
    effect.update(effect_metadata(effect_type))
    if effect_type == 41:
        # Read-only derived view. Evaluators must apply EITHER the raw
        # all_stat_bonus entry OR this expansion, never both.
        effect["expanded_stat_bonuses"] = {stat: value for stat in STAT_TARGETS}
        effect["expanded_is_derived_view"] = True
    return effect


def decode_unique_slot(effect_type: int, values: list[int]) -> Dict[str, Any]:
    v0, v1, v2, v3, v4 = values
    if effect_type in DIRECT_EFFECT_KEYS:
        effect = _effect(effect_type, v0)
        return {"kind": "direct", "status": "structurally_decoded",
                "evaluation_status": "numerically_evaluable",
                "effect_key": effect["effect_key"], "value": v0,
                "effect": effect}
    definition = COMPLEX_UNIQUE_DEFINITIONS.get(effect_type)
    if definition is None:
        return {"kind": "unknown", "status": "unresolved",
                "evaluation_status": "unknown",
                "unresolved_reason": UNKNOWN_REASON, "values": values}
    result: Dict[str, Any] = {"kind": "complex", "key": definition["key"],
                              "parameters": values}
    if definition["evaluation"] == "numeric":
        result["status"] = "structurally_decoded"
        result["evaluation_status"] = "numerically_evaluable"
    elif definition["evaluation"] == "action_only":
        result["status"] = "structurally_decoded"
        result["evaluation_status"] = "action_only_not_numerically_evaluable"
    else:
        result["status"] = "raw_only"
        result["evaluation_status"] = "unknown"
        result["unresolved_reason"] = UNKNOWN_REASON
    if effect_type == 101:
        result.update(condition={"bond_at_least": v0},
                      effects=[_effect(v1, v2), _effect(v3, v4)] if v3 else [_effect(v1, v2)])
    elif effect_type == 112:
        result.update(action="set_failure_rate_zero",
                      activation_scope="training_joined_by_this_card",
                      value_raw=v0,
                      probability=None, probability_status="unknown",
                      timing=None, timing_status="unknown")
    elif effect_type == 113:
        result.update(condition={"friendship_training": True},
                      effects=[_effect(v0, v1)])
    elif effect_type == 115:
        result.update(target="all_deck_cards", timing="initial",
                      effects=[_effect(v0, v1)])
    elif effect_type == 118:
        # Only the bond-threshold check is deterministic. The position
        # selection probability/process are unknown; what is known is the
        # candidate capability that becomes available when the condition is
        # met — not a runtime result.
        result.update(condition={"bond_at_least": v1},
                      deterministic_part="bond_threshold_met",
                      candidate_capability_when_condition_met={
                          "action": "allow_second_training_position",
                          "max_positions": 2,
                      },
                      runtime_result_status="unknown",
                      position_selection_probability_status="unknown",
                      position_selection_process_status="unknown")
    return result


def _unknown_result() -> Dict[str, Any]:
    return {"evaluation_status": "unknown",
            "unresolved_reason": UNKNOWN_REASON,
            "effects": {}, "actions": {}}


def evaluate_decoded(decoded: Mapping[str, Any], context: Mapping[str, Any]) -> Dict[str, Any]:
    """Evaluate decoded unique effects into additive effects and state actions.

    Only slots whose evaluation is a direct restatement of raw MDB fields
    produce numbers. Anything else returns evaluation_status="unknown" with
    empty effects/actions; unknown is NEVER collapsed to a numeric 0.
    """
    if decoded.get("kind") == "direct":
        effect = decoded["effect"]
        return {"evaluation_status": "numerically_evaluable",
                "unresolved_reason": None,
                "effects": {effect["effect_key"]: effect["value"]},
                "actions": {}}
    status = decoded.get("evaluation_status")
    if status == "unknown":
        return _unknown_result()
    typ = int(context.get("_effect_type", 0))
    p = list(decoded.get("parameters", [0, 0, 0, 0, 0]))
    v0, v1, v2, _v3, _v4 = p
    effects: Dict[str, int] = {}
    actions: Dict[str, Any] = {}

    def add_raw(effect: Mapping[str, Any]):
        # Raw application only: a type-41 effect contributes its
        # all_stat_bonus entry; the expanded view is never added on top.
        key = effect["effect_key"]
        value = int(effect["value"])
        if value:
            effects[key] = effects.get(key, 0) + value

    bond = int(context.get("bond", 0))
    if typ == 112:
        # Action structure only. Probability and timing are unknown, so this
        # never decides whether the effect triggers and never sets any actual
        # failure rate; it is not a numeric/runtime evaluation.
        actions["failure_rate_zero"] = {
            "activation_scope": "training_joined_by_this_card",
            "value_raw": v0,
            "probability": None, "probability_status": "unknown",
            "timing": None, "timing_status": "unknown"}
        return {"evaluation_status": "action_only_not_numerically_evaluable",
                "unresolved_reason": None,
                "effects": {}, "actions": actions}
    if typ == 118:
        # Only the bond-threshold check is deterministic (raw field). The
        # capability is expressed as candidate-only; the runtime result and
        # the position selection probability/process stay unknown; no numeric
        # stat effects are produced.
        actions["bond_threshold_met"] = bond >= v1
        if bond >= v1:
            actions["candidate_capability"] = {
                "action": "allow_second_training_position",
                "max_positions": 2,
            }
        actions["runtime_result_status"] = "unknown"
        actions["position_selection_probability_status"] = "unknown"
        actions["position_selection_process_status"] = "unknown"
        return {"evaluation_status": "action_only_not_numerically_evaluable",
                "unresolved_reason": None,
                "effects": {}, "actions": actions}
    if status != "numerically_evaluable":
        return _unknown_result()
    if typ == 101:
        if bond >= v0:
            for effect in decoded.get("effects", []):
                add_raw(effect)
    elif typ == 113:
        if context.get("friendship_training"):
            for effect in decoded.get("effects", []):
                add_raw(effect)
    elif typ == 115:
        actions["all_cards_initial_effect"] = decoded.get("effects", [None])[0]
    else:
        return _unknown_result()
    return {"evaluation_status": "numerically_evaluable",
            "unresolved_reason": None, "effects": effects, "actions": actions}
