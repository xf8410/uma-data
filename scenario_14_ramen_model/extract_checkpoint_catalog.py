#!/usr/bin/env python3
"""Extract Scenario 14 RMJ checkpoints without guessing effect semantics."""
from __future__ import annotations
import argparse, json, sqlite3
from pathlib import Path

TUTORIAL_CATEGORY = 63
TUTORIAL_INDEX = 372

def rows(db: sqlite3.Connection, table: str) -> list[dict]:
    cur = db.execute(f'SELECT * FROM {table} ORDER BY id')
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur]

def build(mdb: Path) -> dict:
    db = sqlite3.connect(f'file:{mdb.resolve()}?mode=ro', uri=True)
    checkpoints = rows(db, 'single_mode_14_check_point')
    settlement = rows(db, 'single_mode_14_check_point_effect')
    passive_tiers = rows(db, 'single_mode_14_check_point_pt_effect')
    tutorial = db.execute(
        'SELECT text FROM text_data WHERE category=? AND "index"=?',
        (TUTORIAL_CATEGORY, TUTORIAL_INDEX),
    ).fetchone()[0]

    out = []
    for cp in checkpoints:
        cp_type = cp['check_point_type']
        success = cp['success_pt']
        great = cp['great_success_pt']
        if great > success:
            result_ranges = [
                {'result_state': 1, 'pt_min': 0, 'pt_max': success - 1, 'threshold_label': 'below_success'},
                {'result_state': 2, 'pt_min': success, 'pt_max': great - 1, 'threshold_label': 'success'},
                {'result_state': 3, 'pt_min': great, 'pt_max': 9999, 'threshold_label': 'great_success'},
            ]
        else:
            result_ranges = [
                {'result_state': 1, 'pt_min': 0, 'pt_max': success - 1, 'threshold_label': 'below_success'},
                {'result_state': 2, 'pt_min': success, 'pt_max': 9999, 'threshold_label': 'success'},
            ]
        effects_by_state = []
        for result in result_ranges:
            state = result['result_state']
            effects_by_state.append({
                **result,
                'effects': [r for r in settlement if r['check_point_type'] == cp_type and r['result_state'] == state],
            })
        out.append({**cp, 'result_ranges': effects_by_state})

    return {
        'scenario_id': 14,
        'schema_version': 1,
        'domain': 'rmj_checkpoint_settlement',
        'notes': [
            'Checkpoint settlement is separate from current-turn ramen action effects.',
            'Result-state ranges are derived directly from success_pt/great_success_pt and existing result_state rows.',
            'great_success_pt=0 on checkpoints 1 and 2 means those checkpoints expose only result states 1 and 2 in MDB.',
            'Settlement effect_type values 4/13/14 are retained raw until their display semantics are independently proven.',
            'checkpoint_pt_effect tiers are stored separately because they are point-dependent passive effects, not settlement rewards.',
        ],
        'tutorial_evidence': {
            'text_data_category': TUTORIAL_CATEGORY,
            'index': TUTORIAL_INDEX,
            'text_ja': tutorial,
        },
        'checkpoints': out,
        'checkpoint_point_passive_tiers': passive_tiers,
    }

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('mdb', type=Path)
    ap.add_argument('-o', '--output', type=Path, default=Path(__file__).with_name('checkpoint_catalog.json'))
    args = ap.parse_args()
    args.output.write_text(json.dumps(build(args.mdb), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

if __name__ == '__main__':
    main()
