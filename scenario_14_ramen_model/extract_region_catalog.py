#!/usr/bin/env python3
"""Extract Scenario 14 region names/effects from a read-only master.mdb."""
from __future__ import annotations
import argparse, json, sqlite3
from pathlib import Path

NAME_CATEGORY = 426
EFFECT_TEXT_CATEGORY = 428
APPLIED_TEXT_CATEGORY = 486

def text_map(db: sqlite3.Connection, category: int) -> dict[int, str]:
    return {i: t for i, t in db.execute(
        'SELECT "index", text FROM text_data WHERE category=? ORDER BY "index"',
        (category,),
    )}

def rows(db: sqlite3.Connection, table: str) -> list[dict]:
    cur = db.execute(f'SELECT * FROM {table} ORDER BY id')
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur]

def build(mdb: Path) -> dict:
    db = sqlite3.connect(f'file:{mdb.resolve()}?mode=ro', uri=True)
    names = text_map(db, NAME_CATEGORY)
    effect_text = text_map(db, EFFECT_TEXT_CATEGORY)
    applied_text = text_map(db, APPLIED_TEXT_CATEGORY)
    effects = rows(db, 'single_mode_14_region_effect')
    bonuses = rows(db, 'single_mode_14_region_effect_bonus')
    feelings = rows(db, 'single_mode_14_region_feeling')
    selects = rows(db, 'single_mode_14_region_select')
    select_turn = {r['region_select_type']: r['turn'] for r in selects}
    result = {
        'scenario_id': 14,
        'evidence': {
            'region_names': {'table': 'text_data', 'category': NAME_CATEGORY},
            'effect_templates': {'table': 'text_data', 'category': EFFECT_TEXT_CATEGORY},
            'applied_effect_templates': {'table': 'text_data', 'category': APPLIED_TEXT_CATEGORY},
            'base_effects': {'table': 'single_mode_14_region_effect'},
            'point_bonuses': {'table': 'single_mode_14_region_effect_bonus'},
            'feelings': {'table': 'single_mode_14_region_feeling'},
            'selection_turns': {'table': 'single_mode_14_region_select'},
        },
        'notes': [
            'Region IDs 1-10 and 11-20 repeat the same ten display names in different selection phases.',
            'effect_value and add_value are retained separately; consumers must select the matching region/effect_type point tier before combining them.',
            'Display text from category 428 is authoritative for user-facing effect wording and percent units where the template contains %.',
        ],
        'selection_phases': selects,
        'regions': [],
    }
    for rid in range(1, 21):
        region_feelings = [r for r in feelings if r['region_id'] == rid]
        if not region_feelings:
            raise ValueError(f'missing feeling rows for region {rid}')
        select_type = region_feelings[0]['region_select_type']
        region_effects = []
        for effect in (r for r in effects if r['region_id'] == rid):
            text_group_id = effect['text_group_id']
            item = dict(effect)
            item['display_template'] = effect_text.get(text_group_id)
            item['applied_template'] = applied_text.get(text_group_id)
            region_effects.append(item)
        result['regions'].append({
            'region_id': rid,
            'name_ja': names.get(rid),
            'region_select_type': select_type,
            'selection_turn': select_turn[select_type],
            'feelings': region_feelings,
            'point_bonus_tiers': [r for r in bonuses if r['region_id'] == rid],
            'effects': region_effects,
        })
    return result

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('mdb', type=Path)
    ap.add_argument('-o', '--output', type=Path, default=Path(__file__).with_name('region_catalog.json'))
    args = ap.parse_args()
    data = build(args.mdb)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

if __name__ == '__main__':
    main()
