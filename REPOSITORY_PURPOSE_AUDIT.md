# 仓库用途审计（新增，不覆盖旧 README）

## 实际用途

这是一个混合型赛马娘研究数据仓库，核心是 `master.mdb` 及大量表导出的 JSON，同时还包含模型、导出物、逆向材料和旧运行时记录。它不只是“App 静态数据 CDN”，旧介绍范围偏窄。

## 目录/文件分类

- 根目录 `master.mdb`、大量 `*.json`、`mdb_tables/`：静态游戏数据库及导出。
- `scenario_08_cook_model/`、`scenario_14_ramen_model/`、`support_card_model/`：专题模型/推导实现。
- `exports/`、`dumps/`：导出或体积材料，是否完整应结合 LFS 与校验清单确认。
- `reverse_engineering/`、`il2cpp_probe/`：逆向和定点探查材料，不等于当前插件 API 实现。
- `training_sessions/`、`summary_logs/`、`debug_logs/`、`history_summary/`：历史运行或总结材料；新运行时观测应与 `uma-runtime-observations` 分工。

## 关联性

为 uma-train、uma-juece及其他分析工具提供静态事实或派生数据；hlpatch 负责运行时采集。目录中存在 hlpatch 端点的旧记录，不代表本仓库提供这些端点。

## 状态

- **实际**：静态数据量大，已有多个模型和研究目录。
- **未完成**：未证明所有 JSON 与当前 MDB 同步、全部 LFS 文件可取、全部模型已校准或旧运行时材料已迁移。
- **猜测**：README 中版本化端点、地址和“实测确认”只应视为对应历史版本证据，不能自动外推到当前 SO。

旧 README 和旧事实全部保留；纠正采用追加记录。