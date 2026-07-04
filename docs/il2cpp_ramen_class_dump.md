# 拉面杯 (Scenario 14) IL2CPP 运行时类 Dump 记录

> 最后更新: 2026-07-04
> 来源: Hachimi URA Plugin `/debug/dumpclass` 端点运行时探测
> 用途: 供 SO 开发时查阅字段偏移、类结构、已知问题

---

## 1. 端口与基础 URL

| 用途 | URL |
|------|-----|
| SO HTTP 端口 | `http://127.0.0.1:18765` |
| App HTTP 端口 | `http://127.0.0.1:18766` |

## 2. SO 端点一览

| 端点 | 说明 |
|------|------|
| `/summary` | 主数据端点，全量育成状态 JSON |
| `/data` | 原始数据 |
| `/scenario` | 剧本信息 |
| `/debug/rameninfo` | 拉面杯调试信息 |
| `/debug/laststep` | 上一步操作 |
| `/event/recommend` | AI 推荐事件 |
| `/inherit/compat` | 继承兼容性 |
| `/log/turn` | 回合日志 |
| `/debug/params` | 参数调试 |
| `/debug/breeders` | 育成者调试 |
| `/debug/cmdinfo` | 指令信息 |
| `/debug/crashlog` | 崩溃日志 |
| `/debug/upload` | 上传调试 |
| `/debug/dumpclass?name=XXX` | IL2CPP 类字段/方法 dump |
| `/debug/storydata` | 剧情数据 |
| `/debug/ramenfields` | 拉面杯数组元素类+字段 dump |
| `/debug/gauge` | CommandFeelingInfoArray 元素类名 (v3.22.38+) |
| `/debug/gauge2` | 遍历 DataSet 所有数组字段元素类名 (v3.22.39+) |
| `/debug/all` | 聚合端点 (需注意死锁: 单次 READ_MUTEX) |
| `/mdb` | MDB 数据库 |
| `/carddb` | 卡牌数据库 |
| `/skilldata` | 技能数据 |
| `/hall` | 技能评分 (v3.19.0+) |
| `/saddles` | 鞍数据 |
| `/saddles-dl` | 鞍下载 |
| `/log` | 日志 |
| `/status` | 状态 |
| `/health` | 健康检查 |
| `/classes/search?name=XXX` | IL2CPP 类名搜索 |

---

## 3. WorkSingleModeScenarioRamenDataSet (24 字段)

**全量字段偏移表:**

| Offset | 字段名 | 类型 | 说明 |
|--------|--------|------|------|
| 16 | CommandInfoArray | List | 训练指令信息数组 |
| 24 | EvaluationInfoArray | List | 评价信息数组 |
| 32 | FeelingReduceTurnInfoArray | List | 感度减少回合信息数组 |
| 40 | FeelingTurnInfoArray | List | **回合感度信息数组** (可能含 TrainingFeelingEntity) |
| 48 | FeelingInfoArray | List | 感度信息数组 (已读，含素材/feeling) |
| 56 | SpecialFeelingNum | ObscuredInt | 特殊感度数量 |
| 80 | ActiveEffectArray | List | 活跃效果数组 |
| 88 | UrafEffectInfo | Object | Uraf 效果信息 |
| 96 | CommandFeelingInfoArray | List | 指令感度信息数组 |
| 104 | TrainingExecInfoArray | List | 训练执行信息数组 |
| 112 | AutoSelectInfo | Object | 自动选择信息 |
| 120 | AutoSelectSetInfo | Object | 自动选择集信息 |
| 128 | RecommendType | ObscuredInt | 推荐类型 |
| 152 | SelectedRegionIdArray | List | 已选地域ID数组 |
| 160 | ReduceBaseTurnInfoArray | List | 基础回合减少信息数组 |
| 168 | CheckPointInfoArray | List | 检查点信息数组 |
| 176 | LastTastingInfo | Object | 最后试食会信息 |
| 184 | CheckPointPt | ObscuredInt | 检查点分数 |
| 204 | ExpectedCheckPointPt | ObscuredInt | 预期检查点分数 |
| 224 | UsedTwinkleTextIdArray | List | 已用闪亮文本ID数组 |
| 232 | AllSelectedRegionIdArray | List | 全部已选地域ID数组 |
| 240 | IsUrafEffectSelectEventChecked | ObscuredBool | Uraf效果选择事件是否已检查 |
| 252 | IsNotGainSpecialFeeling | ObscuredBool | 是否未获得特殊感度 |
| 264 | IsGaugeGained | ObscuredBool | **本轮是否已获得进度条** |

**已知数组元素类型:**

| 数组字段 | 元素类型 | 确认版本 |
|----------|----------|----------|
| CommandInfoArray (16) | `ObscuredSingleModeRamenCommandInfo` | v3.22.28 |
| FeelingInfoArray (48) | 含 FeelingId + FeelingSlotEntity | v3.22.36 |
| CommandFeelingInfoArray (96) | `ObscuredSingleModeRamenCommandFeelingInfo` | v3.22.38 |
| TrainingExecInfoArray (104) | `TrainingExecInfo` | v3.22.28 |
| FeelingReduceTurnInfoArray (32) | 待确认 | |
| FeelingTurnInfoArray (40) | **可能含 TrainingFeelingEntity** | |
| CheckPointInfoArray (168) | 待确认 | |

---

## 4. IL2CPP 类字段 Dump 全量

### 4.1 ObscuredSingleModeRamenCommandInfo

> 来源: 用户手动 dump

| Offset | 字段 | 对应 Getter |
|--------|------|-------------|
| 16 | k__BackingField | get_CommandType (ObscuredInt) |
| 36 | k__BackingField | get_CommandId (ObscuredInt) |
| 56 | k__BackingField | get_ParamsIncDecInfoArray |

**方法:** get_CommandType, get_CommandId, get_ParamsIncDecInfoArray, set_*, .ctor

### 4.2 ObscuredSingleModeRamenCommandFeelingInfo

> 来源: /debug/dumpclass + /debug/gauge 确认元素类型

| Offset | 字段 | 对应 Getter |
|--------|------|-------------|
| 16 | k__BackingField | get_CommandType (ObscuredInt) |
| 36 | k__BackingField | get_CommandId (ObscuredInt) |
| 56 | k__BackingField | get_FeelingId (ObscuredInt) |

**方法:** get_CommandType, get_CommandId, get_FeelingId, set_*, .ctor

**重要:** 这是 `CommandFeelingInfoArray` 的实际元素类型，不是 TrainingFeelingEntity!

### 4.3 TrainingFeelingEntity

> 来源: 用户手动 dump
> 尚未找到此对象存在于哪个数组中! 不在 CommandFeelingInfoArray 中!

| Offset | 字段 | 说明 |
|--------|------|------|
| 16 | _gaugeGainCountDict | `Dictionary<int, FeelingGaugeGainCountVO>` 进度条增量数据 |
| 24 | k__BackingField | get_MainFeeling (ObscuredInt) |
| 32 | k__BackingField | get_TrainingCommandId (ObscuredInt) |

**方法:** get_MainFeeling, get_TrainingCommandId, **GetGainCount**

**SIGSEGV 风险:**
- 手动遍历 `_gaugeGainCountDict` 的 `_entries` 数组会导致 SIGSEGV (int key 是值类型，不是 boxed 引用)
- `GetGainCount(int)` 通过 `call_getter_int_with_arg` 调用也可能导致 SIGSEGV
- 必须在 sigsetjmp 保护下测试，且不能放在 /summary 端点

### 4.4 FeelingSlotEntity

> 来源: 用户手动 dump

| Offset | 字段 |
|--------|------|
| 0 | MAX_COUNT |
| 16 | k__BackingField -> get_FeelingList |

**方法:** get_FeelingList, get_HasTotalCount, HasCount, GetLossFeelingList, GetAdjustedFeelingCount, GetAdjustedTotalFeelingCount

### 4.5 AcquireFeelingRepository

> 来源: 用户手动 dump

| Offset | 字段 |
|--------|------|
| (无字段) | -- |

**方法:** Get, GetBackup

### 4.6 FeelingGaugeGainCountVO

> 来源: 用户手动 dump

| Offset | 字段 |
|--------|------|
| 16 | k__BackingField -> get_FeelingGaugeGainCount (int) |

**方法:** get_FeelingGaugeGainCount, Add, ToString, PrintMembers, op_Inequality, op_Equality, GetHashCode, Equals, $, .ctor

### 4.7 FeelingGaugeCountVO

| Offset | 字段 |
|--------|------|
| 16 | k__BackingField (int) |

### 4.8 NeedAcquireFeelingGaugeCountVO

| Offset | 字段 |
|--------|------|
| 16 | k__BackingField |

**方法:** MaxGaugeGainCount, IsAcquirable

### 4.9 FeelingGaugeGainCountCacheHolder

| Offset | 字段 |
|--------|------|
| 16 | k__BackingField |

### 4.10 AcquireFeelingEntity

| Offset | 字段 |
|--------|------|
| 16 | k__BackingField |
| 24 | k__BackingField |
| 32 | k__BackingField |

**方法:** GainableCount, GainedCount

### 4.11 ObscuredSingleModeRamenFeeling

| Offset | 字段 |
|--------|------|
| 16 | k__BackingField |
| 24 | k__BackingField |

### 4.12 SingleMode14TwinkleRamen

> 来源: /debug/dumpclass

| Offset | 字段 | 类型 |
|--------|------|------|
| 16 | Id | int |
| 20 | TextGroup | int |
| 24 | TextNumber | int |
| 28 | CheckPointType | int |
| 32 | ResultState | int |
| 36 | TextType | int |
| 40 | TextTypeValue | int |

**无自定义方法** (仅 Object 基类方法)

### 4.13 SingleModeScenarioRamenDefine

31 个字段 (mdb 定义类，非运行时状态)

### 4.14 TrainingExecInfo

| Offset | 字段 |
|--------|------|
| 16 | k__BackingField |
| 24 | k__BackingField |

### 4.15 ActiveEffectInfo

| Offset | 字段 |
|--------|------|
| 16 | k__BackingField (category, int) |
| 24 | k__BackingField (id, int) |
| 32 | k__BackingField (value, int) |

### 4.16 UrafEffectInfo

| Offset | 字段 |
|--------|------|
| 16 | k__BackingField |
| 24 | k__BackingField |

### 4.17 AutoSelectInfo

| Offset | 字段 |
|--------|------|
| 16 | k__BackingField |
| 24 | k__BackingField |
| 32 | k__BackingField |
| 40 | k__BackingField |

### 4.18 AutoSelectSetInfo

| Offset | 字段 |
|--------|------|
| 16 | k__BackingField |
| 24 | k__BackingField |
| 32 | k__BackingField |
| 40 | k__BackingField |
| 48 | k__BackingField |

### 4.19 ReduceBaseTurnInfo

| Offset | 字段 |
|--------|------|
| 16 | k__BackingField |
| 24 | k__BackingField |

### 4.20 ParamsIncDecInfo

**不存在!** dump 返回空，此类在 IL2CPP 中未定义。

---

## 5. ObscuredInt 内存布局

> 来源: Anti-Cheat Toolkit dump.cs + 实测确认

```
offset 0x10: currentCryptoKey (Int32) -- 解密密钥
offset 0x14: hiddenValue (Int32)     -- 加密值
offset 0x18: inited (Boolean)
offset 0x1C: fakeValue (Int32)
offset 0x20: fakeValueActive (Boolean)
```

**解密:** `decrypted = hiddenValue ^ currentCryptoKey`

**字段跨度:** 每个 ObscuredInt 占 0x14 (20) 字节，所以相邻 ObscuredInt 间距 = 0x14 (如 offset 16->36->56)

---

## 6. IL2CPP List 内存布局

```
offset 0x10: _items (Array pointer)
offset 0x18: _size (int, 即 count)
offset 0x1C: _version (int)
```

SO 中用常量:
- `IL2CPP_LIST_COUNT_OFF` = list 对象上 count 的偏移
- `IL2CPP_LIST_ITEMS_OFF` = list 对象上 items 数组指针的偏移
- `IL2CPP_LIST_ITEM_SIZE` = 8 (64-bit 指针)

---

## 7. Dictionary 内存布局参考

手动遍历 Dictionary 的 _entries 数组已证实会导致 SIGSEGV!
原因: `Dictionary<int, VO>` 的 int key 是值类型，不是 boxed 引用，按指针读会踩野指针。

**安全方式:** 通过 `il2cpp_runtime_invoke` 调用方法 (如 `GetGainCount(int)`), 而非手动遍历内存。

---

## 8. 关键发现与踩坑记录

### 8.1 CommandFeelingInfoArray != TrainingFeelingEntity

初始假设 `CommandFeelingInfoArray` 的元素是 `TrainingFeelingEntity`，实际是 `ObscuredSingleModeRamenCommandFeelingInfo` (3 个 ObscuredInt: CommandType, CommandId, FeelingId)。gauge 增量数据不在此数组中。

### 8.2 危险操作不放 /summary

gauge 读取 (无论是手动遍历 dict 还是调用 GetGainCount) 可能导致 SIGSEGV。必须放在独立 /debug/gauge 端点，崩了不影响 /summary。用户明确纠正过"为什么加 summary 里面"。

### 8.3 sigsetjmp 保护是必须的

/debug 端点必须:
1. 获取 `READ_MUTEX` 锁
2. 设置 `sigsetjmp` 恢复点
3. 设置 `SIGSEGV_RECOVERY` 标志
4. `panic::catch_unwind` 包裹

缺少 sigsetjmp 保护时，SIGSEGV 会直接杀进程导致游戏闪退。

### 8.4 IsGaugeGained 字段

DataSet offset 264 有 `IsGaugeGained` (ObscuredBool)，表示本轮是否已获得进度条。这是已知的 gauge 相关字段，但增量数据 (每格加多少) 仍需从 TrainingFeelingEntity 获取。

### 8.5 /debug/all 死锁

`read_summary` 拿 `READ_MUTEX` 后 `debug_storydata` 也要拿 `READ_MUTEX`，Rust `Mutex` 非重入 -> 死锁。v3.22.35 修复: `/debug/all` 只获取一次 `READ_MUTEX`，内部直接调用 `_inner` 函数跳过各自的 mutex 获取。

### 8.6 年次结算闪退

`push_loop` 中 `read_summary` 的 `il2cpp_runtime_invoke` 在游戏状态转换时访问野指针 -> SIGSEGV。用 sigsetjmp/longjmp 捕获后冷却 60s 跳过。

### 8.7 事件效果数值不在 IL2CPP 也不在 mdb

IL2CPP 运行时类不存储事件选择效果数值，mdb 也不含。只能从攻略站/wiki 抓取。

### 8.8 SO 文件名问题

Android 下载管理器会自动给 SO 文件名加 `(1)` 后缀，导致注入失败。需要手动重命名去掉括号后缀。v3.18.7 修复。

---

## 9. BWiki 攻略站确认的拉面杯机制数据

| 机制 | 无友人 | 旧绿帽/B95友人 | 新SSR绿帽 |
|------|--------|---------------|-----------|
| 基础获得能量总和 | 3 | 5 | 10 |
| 选择地区后获得的诀窍数量 | 1 | 1 | 2 |
| 出行事件获得的秘方数量 | 0 | 1 | 2 |
| 夏季集训每回合诀窍 | -- | -- | 三种MAX(+7) |

- 每次制作拉面最多用 2 个秘方
- 进度条 10 格满才出 1 个素材 (SOZAI_GAUGE_MAX=10, 不是 Wiki 写的 7)
- 素材 10 槽 FIFO 共享上限: 3 种素材共享 10 个槽位，满了新素材顶掉最旧的

---

## 10. 待确认项

- [ ] TrainingFeelingEntity 在哪个数组/对象中? (FeelingTurnInfoArray 最可疑)
- [ ] 进度条增量: 普通人头/彩圈各加几格?
- [ ] FeelingReduceTurnInfoArray / CheckPointInfoArray 元素类型
- [ ] support_cards 为空 bug (/summary 返回 [])
- [ ] GUI 版本号未同步 (App 显示 3.22.28，API 返回 3.22.39)
- [ ] 种马 (继承/因子) 部分数据读取
