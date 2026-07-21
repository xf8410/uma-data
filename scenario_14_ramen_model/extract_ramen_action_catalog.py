#!/usr/bin/env python3
"""Build current-turn ramen action effects from Scenario 14 MDB tables."""
from __future__ import annotations
import argparse, json, sqlite3
from pathlib import Path

EFFECT_TEXT_CATEGORY = 427
TUTORIAL_CATEGORY = 63
TUTORIAL_INDEX = 366

def rows(db: sqlite3.Connection, table: str) -> list[dict]:
    cur = db.execute(f'SELECT * FROM {table} ORDER BY id')
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur]

def text_map(db: sqlite3.Connection, category: int) -> dict[int, str]:
    return {i: t for i, t in db.execute(
        'SELECT "index", text FROM text_data WHERE category=? ORDER BY "index"',
        (category,),
    )}

def build(mdb: Path) -> dict:
    db = sqlite3.connect(f'file:{mdb.resolve()}?mode=ro', uri=True)
    display = text_map(db, EFFECT_TEXT_CATEGORY)
    tutorial = text_map(db, TUTORIAL_CATEGORY)[TUTORIAL_INDEX]
    effects = rows(db, 'single_mode_14_basic_effect')
    point_gains = {
        r['check_point_type']: r['gain_pt']
        for r in rows(db, 'single_mode_14_check_point_pt')
    }
    stages = []
    for stage in (1, 2, 3):
        stage_effects = []
        for effect in (r for r in effects if r['check_point_type'] == stage):
            item = dict(effect)
            item['display_text_ja'] = display.get(effect['id'])
            stage_effects.append(item)
        stages.append({
            'stage': stage,
            'effect_duration': 'current_turn',
            'base_checkpoint_pt_gain': point_gains[stage],
            'effects': stage_effects,
        })
    return {
        'scenario_id': 14,
        'schema_version': 1,
        'domain': 'ramen_action_current_turn',
        'notes': [
            'These are effects of making/eating ramen for the current turn; they are not RMJ checkpoint settlement rewards.',
            'Stage 1 effect id 3 is bond gauge +10 and belongs to the ramen action effect set.',
            'Conditions and raw effect_type/effect_value are retained; consumers should prefer display_text_ja for units.',
            'The catalog does not assert additive versus multiplicative stacking with region effects.',
        ],
        'tutorial_evidence': {
            'text_data_category': TUTORIAL_CATEGORY,
            'index': TUTORIAL_INDEX,
            'text_ja': tutorial,
        },
        'effect_text_source': {
            'table': 'text_data',
            'category': EFFECT_TEXT_CATEGORY,
        },
        'stages': stages,
    }

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('mdb', type=Path)
    ap.add_argument('-o', '--output', type=Path, default=Path(__file__).with_name('ramen_action_catalog.json'))
    args = ap.parse_args()
    args.output.write_text(json.dumps(build(args.mdb), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

if __name__ == '__main__':
    main()
