#!/usr/bin/env python3
"""Compare Scenario 14 ramen-training formula candidates inside the user's project.

The ordinary training inputs follow UmaAI's verified lower-layer structure. This tool
only varies the still-unverified placement of Scenario 14 region/ramen effects,
friendship bonus, caps and rounding. Candidate matches are evidence for follow-up;
they are not promoted automatically to the production scoring formula.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

STAGE_EFFECTS = {
    1: {"training": 15, "friendship": 0, "failure_drop": 30, "cap": 0},
    2: {"training": 15, "friendship": 30, "failure_drop": 50, "cap": 20},
    3: {"training": 15, "friendship": 45, "failure_drop": 100, "cap": 40},
}


def umaai_card_multiplier(sample: Mapping[str, Any], training_bonus: float,
                           friendship_multiplier: float) -> float:
    """UmaAI card/head/motivation/friendship multiplier before scenario effects."""
    heads = float(sample.get("head_count", 0))
    motivation = float(sample.get("motivation", 3))
    motivation_bonus = float(sample.get("motivation_bonus", 0))
    head_multiplier = 1.0 + 0.05 * heads
    training_multiplier = 1.0 + 0.01 * training_bonus
    mood_multiplier = 1.0 + 0.1 * (motivation - 3.0) * (1.0 + 0.01 * motivation_bonus)
    return head_multiplier * training_multiplier * mood_multiplier * friendship_multiplier


def card_friendship_multiplier(friendship_bonuses: Iterable[float]) -> float:
    result = 1.0
    for value in friendship_bonuses:
        result *= 1.0 + 0.01 * float(value)
    return result


def friendship_candidates(friendship_bonuses: List[float], ramen_bonus: float) -> Dict[str, float]:
    base = card_friendship_multiplier(friendship_bonuses)
    if not friendship_bonuses or ramen_bonus <= 0:
        return {"none": base}
    return {
        "scenario_once": base * (1.0 + 0.01 * ramen_bonus),
        "add_to_each_shining_card": card_friendship_multiplier(
            [value + ramen_bonus for value in friendship_bonuses]),
    }


def _round(value: float, mode: str) -> int:
    if mode == "floor":
        return math.floor(value)
    if mode == "truncate":
        return int(value)
    raise ValueError("unknown rounding mode: " + mode)


def evaluate_candidates(sample: Mapping[str, Any]) -> Dict[str, Any]:
    stage = int(sample["ramen_stage"])
    if stage not in STAGE_EFFECTS:
        raise ValueError("ramen_stage must be 1, 2 or 3")
    effects = STAGE_EFFECTS[stage]
    basic = float(sample["basic_value"])
    growth = 1.0 + 0.01 * float(sample.get("growth_bonus", 0))
    support_training = float(sample.get("support_training_bonus", 0))
    region_training = float(sample.get("region_training_bonus", 0))
    friendships = [float(x) for x in sample.get("friendship_bonuses", [])]
    observed = sample.get("observed_gain")
    observed = None if observed is None else int(observed)
    normal_cap = int(sample.get("normal_cap", 100))
    ramen_training = float(effects["training"])
    cap = normal_cap + int(effects["cap"])

    # The three relationships under investigation. Names describe only candidates.
    training_candidates = {
        "all_training_additive": {
            "card_training": support_training + region_training + ramen_training,
            "scenario_multiplier": 1.0,
        },
        "region_and_ramen_scenario_additive": {
            "card_training": support_training,
            "scenario_multiplier": 1.0 + 0.01 * (region_training + ramen_training),
        },
        "region_and_ramen_independent": {
            "card_training": support_training,
            "scenario_multiplier": (1.0 + 0.01 * region_training) * (1.0 + 0.01 * ramen_training),
        },
    }
    friendship_options = friendship_candidates(friendships, float(effects["friendship"]))

    rows: List[Dict[str, Any]] = []
    for (training_name, training), (friendship_name, friendship), rounding, cap_scope in itertools.product(
            training_candidates.items(), friendship_options.items(),
            ("floor", "truncate"), ("final", "umaai_lower_then_final")):
        card_multiplier = umaai_card_multiplier(sample, training["card_training"], friendship)
        lower_raw = basic * card_multiplier * growth
        if cap_scope == "umaai_lower_then_final":
            lower = min(_round(lower_raw, rounding), cap)
            final_raw = lower * training["scenario_multiplier"]
            predicted = min(_round(final_raw, rounding), cap)
        else:
            final_raw = lower_raw * training["scenario_multiplier"]
            predicted = min(_round(final_raw, rounding), cap)
        rows.append({
            "training_relation": training_name,
            "friendship_relation": friendship_name,
            "rounding": rounding,
            "cap_scope": cap_scope,
            "lower_raw": lower_raw,
            "final_raw": final_raw,
            "cap": cap,
            "predicted_gain": predicted,
            "matches_observed": observed is not None and predicted == observed,
        })

    # Collapse mechanically duplicate rows while preserving every explanation.
    grouped: Dict[int, Dict[str, Any]] = {}
    for row in rows:
        gain = row["predicted_gain"]
        group = grouped.setdefault(gain, {
            "predicted_gain": gain,
            "matches_observed": observed is not None and gain == observed,
            "candidate_explanations": [],
        })
        group["candidate_explanations"].append({k: row[k] for k in (
            "training_relation", "friendship_relation", "rounding", "cap_scope",
            "lower_raw", "final_raw", "cap")})

    matches = [row for row in rows if row["matches_observed"]]
    return {
        "schema_version": 1,
        "mode": "scenario_14_ramen_training_candidate_comparison",
        "status": "candidate_only_not_for_production_scoring",
        "stage_effects": effects,
        "observed_gain": observed,
        "prediction_groups": [grouped[key] for key in sorted(grouped)],
        "exact_match_count": len(matches),
        "exact_matches": matches,
        "interpretation": (
            "No observation supplied; predictions only." if observed is None else
            "No candidate matched; inputs or candidate set are incomplete." if not matches else
            "One or more candidates matched. Use additional discriminating samples before confirmation."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sample", type=Path, help="one normalized training sample JSON")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    with args.sample.open(encoding="utf-8") as stream:
        sample = json.load(stream)
    print(json.dumps(evaluate_candidates(sample), ensure_ascii=False,
                     indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
