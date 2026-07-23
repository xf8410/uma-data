#!/usr/bin/env python3
"""Evidence-bounded Scenario 14 runtime snapshot replay simulator.

This module never reconstructs the server-side training gain formula. Training gains
are passed through from the runtime snapshot; only catalog-backed region resolution,
resource affordability, acquisition-gauge/FIFO transitions and checkpoint distances
are simulated.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

BASE = Path(__file__).resolve().parent


def load_json(path: Path) -> Dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def load_catalogs(base: Path = BASE) -> Dict[str, Dict[str, Any]]:
    return {
        "regions": load_json(base / "region_catalog.json"),
        "resources": load_json(base / "resource_economy.json"),
        "gauges": load_json(base / "acquisition_gauge_catalog.json"),
        "actions": load_json(base / "ramen_action_catalog.json"),
        "checkpoints": load_json(base / "checkpoint_catalog.json"),
    }


def _matching_tier(region: Mapping[str, Any], effect_type: int, pt: int) -> Optional[Mapping[str, Any]]:
    for tier in region.get("point_bonus_tiers", []):
        if tier.get("effect_type") == effect_type and tier.get("min_pt", 1) <= pt <= tier.get("max_pt", -1):
            return tier
    return None


def resolve_regions(catalog: Mapping[str, Any], region_ids: Iterable[int], checkpoint_pt: int) -> List[Dict[str, Any]]:
    """Resolve official names and final catalog effect values at the supplied point tier."""
    by_id = {row["region_id"]: row for row in catalog.get("regions", [])}
    result: List[Dict[str, Any]] = []
    for region_id in region_ids:
        region = by_id.get(region_id)
        if region is None:
            result.append({"region_id": region_id, "status": "unknown_region"})
            continue
        effects = []
        for effect in region.get("effects", []):
            effect_type = effect["effect_type"]
            tier = _matching_tier(region, effect_type, checkpoint_pt)
            add_value = tier["add_value"] if tier else 0
            effects.append({
                "effect_id": effect["id"],
                "effect_type": effect_type,
                "base_value": effect["effect_value"],
                "add_value": add_value,
                "resolved_value": effect["effect_value"] + add_value,
                "display_template": effect.get("display_template"),
                "conditions": [
                    {"type": effect.get(f"condition_type_{i}", 0), "value": effect.get(f"condition_value_{i}", 0)}
                    for i in range(1, 4)
                    if effect.get(f"condition_type_{i}", 0) != 0
                ],
                "bonus_tier": None if tier is None else {
                    "min_pt": tier["min_pt"], "max_pt": tier["max_pt"]
                },
            })
        result.append({
            "region_id": region_id,
            "name_ja": region["name_ja"],
            "region_select_type": region["region_select_type"],
            "status": "resolved",
            "effects": effects,
        })
    return result


def _inventory_queue(ramen: Mapping[str, Any]) -> tuple[List[int], bool]:
    indexed = []
    for offset, item in enumerate(ramen.get("feeling_info") or []):
        feeling_id = item.get("FeelingId", item.get("feeling_id"))
        index = item.get("FeelingIndex", item.get("feeling_index", offset))
        if feeling_id in (1, 2, 3):
            indexed.append((index, feeling_id))
    if indexed:
        return [item[1] for item in sorted(indexed)], True
    queue: List[int] = []
    for feeling_id, count in enumerate(ramen.get("sozai") or [], 1):
        if feeling_id <= 3:
            queue.extend([feeling_id] * max(0, int(count)))
    return queue, False


def simulate_gauges(gauge_catalog: Mapping[str, Any], ramen: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Replay final runtime decrement vectors; do not derive their components."""
    rules = gauge_catalog["acquisition_rules"]
    threshold = rules["threshold"]
    capacity = rules["inventory"]["shared_capacity"]
    current = {
        int(item["feeling_id"]): int(item["remaining"])
        for item in ramen.get("acquisition_gauges") or []
        if item.get("feeling_id") in (1, 2, 3) and item.get("remaining") is not None
    }
    queue, order_known = _inventory_queue(ramen)
    output = []
    for vector in ramen.get("command_gauge_vectors") or []:
        projected = list(queue)
        gained: List[int] = []
        evicted: List[Optional[int]] = []
        after_remaining = dict(current)
        decrements: Dict[int, int] = {}
        for item in vector.get("progress") or []:
            feeling_id = int(item.get("feeling_id", -1))
            decrement = int(item.get("remaining", -1))
            if feeling_id not in (1, 2, 3) or decrement < 0 or feeling_id not in current:
                continue
            decrements[feeling_id] = decrement
            if decrement >= current[feeling_id]:
                gained.append(feeling_id)
                while len(projected) >= capacity:
                    evicted.append(projected.pop(0) if order_known else None)
                projected.append(feeling_id)
                after_remaining[feeling_id] = threshold
            else:
                after_remaining[feeling_id] = current[feeling_id] - decrement
        output.append({
            "command_id": vector.get("command_id"),
            "source": "runtime_final_vector",
            "decrements": decrements,
            "gained_feelings": gained,
            "remaining_after": after_remaining,
            "inventory_after": projected,
            "inventory_order_known": order_known,
            "evicted_feelings": evicted,
            "overflow_carried": False,
        })
    return output


def recipe_affordability(resource_catalog: Mapping[str, Any], ramen: Mapping[str, Any]) -> List[Dict[str, Any]]:
    counts = [0] + [max(0, int(x)) for x in (ramen.get("sozai") or [0, 0, 0])[:3]]
    while len(counts) < 4:
        counts.append(0)
    special = max(0, int(ramen.get("special_feeling_num", 0)))
    max_substitutions = resource_catalog["special_item"]["max_substitutions_per_ramen"]
    selected = set(ramen.get("selected_region_ids") or [])
    output = []
    for recipe in resource_catalog.get("recipes", []):
        if selected and recipe["region_id"] not in selected:
            continue
        cost = recipe["cost"]
        deficits = {
            feeling_id: max(0, int(cost[str(feeling_id)]) - counts[feeling_id])
            for feeling_id in range(1, 4)
        }
        needed = sum(deficits.values())
        usable_special = min(special, max_substitutions)
        output.append({
            "region_id": recipe["region_id"],
            "cost": cost,
            "deficits": deficits,
            "special_needed": needed,
            "craftable": needed <= usable_special,
        })
    return output


def checkpoint_projection(checkpoint_catalog: Mapping[str, Any], action_catalog: Mapping[str, Any],
                          turn: int, checkpoint_pt: int, planned_ramen_count: int = 0) -> Dict[str, Any]:
    checkpoints = sorted(checkpoint_catalog.get("checkpoints", []), key=lambda row: row["turn"])
    upcoming = next((row for row in checkpoints if row["turn"] >= turn), None)
    if upcoming is None:
        return {"status": "complete", "current_pt": checkpoint_pt}
    stage = 1 if upcoming["turn"] == 24 else 2 if upcoming["turn"] == 48 else 3
    stage_row = next(row for row in action_catalog.get("stages", []) if row.get("stage") == stage)
    base_gain = int(stage_row["base_checkpoint_pt_gain"])
    projected = checkpoint_pt + max(0, planned_ramen_count) * base_gain
    success = upcoming["success_pt"]
    great = upcoming["great_success_pt"]
    return {
        "status": "projected",
        "checkpoint_turn": upcoming["turn"],
        "turns_remaining": upcoming["turn"] - turn,
        "stage": stage,
        "current_pt": checkpoint_pt,
        "planned_ramen_count": max(0, planned_ramen_count),
        "base_pt_per_ramen": base_gain,
        "projected_pt": projected,
        "success_pt": success,
        "success_shortfall": max(0, success - projected),
        "great_success_pt": great or None,
        "great_success_shortfall": None if not great else max(0, great - projected),
    }


def simulate(snapshot: Mapping[str, Any], catalogs: Optional[Mapping[str, Mapping[str, Any]]] = None) -> Dict[str, Any]:
    catalogs = catalogs or load_catalogs()
    ramen = snapshot.get("ramen") or {}
    # Plugin /summary emits "checkpoint_pt"; older snapshots used
    # "check_point_pt". Accept both spellings at both nesting levels.
    checkpoint_pt = int(
        ramen.get(
            "checkpoint_pt",
            ramen.get(
                "check_point_pt",
                snapshot.get("checkpoint_pt", snapshot.get("check_point_pt", 0)),
            ),
        )
    )
    trainings = snapshot.get("trainings") or []
    return {
        "schema_version": 1,
        "mode": "scenario_14_runtime_snapshot_replay",
        "turn": int(snapshot.get("turn", 0)),
        "training_gains": [
            {"command_id": row.get("command_id"), "gains": row.get("gains", {}), "source": "runtime_final_gains"}
            for row in trainings
        ],
        "regions": resolve_regions(catalogs["regions"], ramen.get("selected_region_ids") or [], checkpoint_pt),
        "gauges": simulate_gauges(catalogs["gauges"], ramen),
        "recipes": recipe_affordability(catalogs["resources"], ramen),
        "checkpoint": checkpoint_projection(
            catalogs["checkpoints"], catalogs["actions"], int(snapshot.get("turn", 0)),
            checkpoint_pt, int(snapshot.get("planned_ramen_count", 0))),
        "unknowns": [
            "server-side training gain decomposition and rounding",
            "race gauge vectors and race-result dependence",
            "year-end normal-item-to-vital formula",
            "same-turn ordering of ramen consumption, gauge completion and inventory insertion",
            "full action transition probabilities for race/rest/outing/events",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path, help="normalized runtime snapshot JSON")
    parser.add_argument("--catalog-dir", type=Path, default=BASE)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    result = simulate(load_json(args.snapshot), load_catalogs(args.catalog_dir))
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
