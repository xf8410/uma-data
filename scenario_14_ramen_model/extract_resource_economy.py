#!/usr/bin/env python3
"""Build the Scenario 14 ramen resource catalog from master.mdb."""
from __future__ import annotations
import argparse, json, sqlite3
from pathlib import Path

ITEM_TEXT_CATEGORY = 465
SUPPORT_NAME_CATEGORY = 75
TUTORIAL_CATEGORY = 63
TUTORIAL_INDEXES = (365, 370, 371, 373)
NORMAL_SHARED_CAP = 10
SPECIAL_CAP = 4
MAX_SPECIAL_PER_RAMEN = 2

def rows(db: sqlite3.Connection, table: str) -> list[dict]:
    cur = db.execute(f'SELECT * FROM {table} ORDER BY id')
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur]

def texts(db: sqlite3.Connection, category: int) -> dict[int, str]:
    return {i: t for i, t in db.execute(
        'SELECT "index", text FROM text_data WHERE category=? ORDER BY "index"',
        (category,),
    )}

def build(mdb: Path) -> dict:
    db = sqlite3.connect(f'file:{mdb.resolve()}?mode=ro', uri=True)
    item_names = texts(db, ITEM_TEXT_CATEGORY)
    support_names = texts(db, SUPPORT_NAME_CATEGORY)
    tutorials = texts(db, TUTORIAL_CATEGORY)
    feelings = rows(db, 'single_mode_14_region_feeling')
    fixed_gains = rows(db, 'single_mode_14_special_gain_turn')
    outings = rows(db, 'single_mode_14_outing_effect')

    recipes = []
    for region_id in range(1, 21):
        recipe_rows = [r for r in feelings if r['region_id'] == region_id]
        if len(recipe_rows) != 3:
            raise ValueError(f'region {region_id}: expected 3 recipe rows')
        recipe = {str(r['feeling_id']): r['feeling_num'] for r in recipe_rows}
        recipes.append({
            'region_id': region_id,
            'region_select_type': recipe_rows[0]['region_select_type'],
            'cost': recipe,
            'normal_item_total': sum(recipe.values()),
        })

    outing_rewards = []
    for r in outings:
        outing_rewards.append({
            **r,
            'support_card_name_ja': support_names.get(r['support_card_id']),
        })

    return {
        'scenario_id': 14,
        'schema_version': 1,
        'normal_items': {
            'shared_inventory_cap': NORMAL_SHARED_CAP,
            'items': [
                {'feeling_id': i, 'name_ja': item_names[i]}
                for i in (1, 2, 3)
            ],
            'acquisition': 'Each type has a separate acquisition gauge; a full gauge grants one matching item.',
            'year_end_reset': {
                'timing': 'after December second-half turn ends',
                'clears_all_normal_items': True,
                'remaining_items_restore_vital': True,
                'vital_formula_verified': False,
            },
        },
        'special_item': {
            'name_ja': '隠し味の秘訣',
            'inventory_cap': SPECIAL_CAP,
            'shares_normal_inventory': False,
            'can_substitute_any_normal_item': True,
            'max_substitutions_per_ramen': MAX_SPECIAL_PER_RAMEN,
            'cleared_at_year_end': False,
            'fixed_turn_gains': fixed_gains,
            'outing_rewards': outing_rewards,
        },
        'recipes': recipes,
        'tutorial_evidence': [
            {'text_data_category': TUTORIAL_CATEGORY, 'index': i, 'text_ja': tutorials[i]}
            for i in TUTORIAL_INDEXES
        ],
        'decision_constraints': [
            'Never consume ramen only to avoid special-item overflow; jointly evaluate the following main action, vital, and training value.',
            'Ramen training effects last for the current turn, so ramen followed by outing/rest usually wastes training-only effects.',
            'Before the December second-half turn ends, compare using normal items with their verified year-end vital recovery value.',
            'Special-item substitution should consider recipe deficits, future gauge gains, shared-cap overflow, and incoming fixed/outing gains.',
        ],
        'unknowns': [
            'Exact acquisition-gauge increment and threshold formula is not asserted by this MDB catalog.',
            'Exact vital recovery per normal item at year-end is not asserted by the inspected tables/text.',
            'Whether fixed turn 1/24/48 gains occur before or after region selection needs runtime ordering evidence.',
        ],
    }

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('mdb', type=Path)
    ap.add_argument('-o', '--output', type=Path, default=Path(__file__).with_name('resource_economy.json'))
    args = ap.parse_args()
    args.output.write_text(json.dumps(build(args.mdb), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

if __name__ == '__main__':
    main()
