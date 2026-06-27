# UMA AI Data

赛马娘AI助手静态数据仓库，供App远程加载。

## 数据文件

| 文件 | 记录数 | 大小 | 说明 |
|------|--------|------|------|
| uma_names.json | 813 | 53KB | 角色名称映射（日文名→中文昵称） |
| uma_events.json | 8063 | 1.8MB | 育成事件（含选项和效果） |
| uma_skills.json | 2008 | 179KB | 技能数据 |
| uma_factors.json | 2436 | 256KB | 因子效果 |

## 使用方式

直接用 raw.githubusercontent.com 的URL加载：

```
https://raw.githubusercontent.com/xf8410/uma-data/main/uma_names.json
```

App端用 OkHttp 或 HttpURLConnection 下载，缓存到本地。
