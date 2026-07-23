# 通用支援卡模拟目录

本目录把完整 `master.mdb` 支援卡表转换为与剧本无关的标准目录，供 Scenario 14、Scenario 8 和旧剧本模拟器复用。

## 生成

```bash
python support_card_model/extract_support_card_catalog.py master.mdb \
  -o support_card_model/support_card_catalog.json
python support_card_model/build_support_card_report.py \
  support_card_model/support_card_catalog.json \
  -o support_card_model/support_card_effect_report.json
```

- `support_card_catalog.json`：模拟器直接消费的标准目录；
- `support_card_effect_report.json`：逐卡审计报告，明确列出每张卡五档突破普通效果、等级断点、官方固有说明、原始参数、Hint 事件奖励行、条件合并视图以及覆盖矩阵。

## 证据边界

- 机制与原始数值仅来自 master.mdb；中文展示名（display_name_zh）与效果分类（effect_category）为项目内人工命名元数据，不是 MDB 原始字段；证据材料限于 uma-data 自有 JSON、reverse_engineering 与用户确认值，不使用外部模拟器、BWIKI 或攻略站公式。
- 复杂固有（type 101–122）只保留 MDB 原始参数与 `text_data category=155` 官方文本；状态分为 `structurally_decoded`（可安全描述结构或动作，不一定可计算）、`numerically_evaluable`（仅指 MDB 条件与直接值可生成静态数值结果——type 115 的数值经 actions 携带、目标与时机以 category 155 文本为准；不代表完整训练公式、叠加顺序、取整或剧本倍率已确认）、`action_only_not_numerically_evaluable`（如 112/118，只输出动作结构，不做随机求值，不产出数值属性效果）与 `unknown_formula`（结构可能已知，但精确数值求值未确认；不求值且不得视为 0）。
- type 112（中山庆典）只确认“有时令参加训练失败率变为 0”：`probability`/`timing` 均为 unknown，不输出 `probability_percent`。

## 命名与分类

- 机器键保持消费者兼容（`speed_bonus` 等不变）；新增 `effect_category` / `target` / `display_name_zh` 元数据。
- B 加成（`training_stat_bonus`）：type 3–7 = 速度/耐力/力量/根性/智力加成；type 41 = 全属性加成，保留原始 `all_stat_bonus` 并提供只读派生展开 `expanded_stat_bonuses`，求值时二选一，不得双算。
- type 30 = 技能Pt加成（`skill_pt_bonus`），独立列出；type 9–13 = 初始五维属性，与 B 加成严格区分。
- `single_mode_hint_gain` 的 `hint_gain_type=1` 输出为“Hint 事件速度/耐力/力量/根性/智力/技能Pt奖励”（`hint_event_reward`），绝不进入 B 字段；条件行（`condition_set_id` 非零）单列，行选择语义（priority 覆盖规则）为 unknown。

## 输入表

- `support_card_data`、`support_card_effect_table`、`support_card_unique_effect`、`support_card_limit`、`support_card_group`、`single_mode_hint_gain`
- `text_data`（category 75/76/77/151/154/155）

## 输出边界

- 覆盖全部 541 张支援卡；
- 保存 0～4 突对应的等级上限及已生效普通效果，以及效果发生变化的等级断点；
- 普通效果 type 1～32 使用 MDB `text_data category=151` 名称、category 154 描述和稳定键；
- 固有效果始终保留完整原始字段；MDB 的 `lv` 标为 `lv_raw`，不在缺少独立证据时猜成解锁等级；
- 带羁绊阈值的固有（type 101）提供 `resolved_effects_when_condition_met` 合并视图：仅当全部嵌套效果属于直接效果安全白名单时生成，普通与固有来源分列后再合并；合并视图 `view_kind="static_conditional_merge_not_runtime_evaluation"`（条件满足时的静态效果合并视图，非完整运行时求值），合并值带 `condition_status="conditional_not_passive"`，只在条件满足时生效，默认卡面板仍以普通效果为准；
- 支援卡事件归属链、友人/团队卡点击出行等行为、`effect_id` 含义、`support_card_team_score_bonus` 语义均标 unknown 或 raw_only（见报告覆盖矩阵），剧本专属效果不并入通用逐卡训练效果。

目录本身只描述卡片效果，不包含任何特定剧本 Link、菜谱、地区或场景倍率。剧本模拟器应在其自身模块中叠加剧本规则。
