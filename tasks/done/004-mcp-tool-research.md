# 004 - MCP 工具能力深度研究

**创建**: 2026-03-27
**状态**: ✅ 已完成（2026-03-28 更新）

## MCP 服务器工具清单（82.156.17.205）

| 工具 | 参数 | 功能 | 状态 |
|------|------|------|------|
| `brief` | symbol | 基本信息（代码/名称/行业/PE/PB/ROE/价格/均价/振幅） | ✅ 稳定 |
| `medium` | symbol | 中等信息（+行业概念/主力净流入） | ✅ 稳定 |
| `full` | symbol | 完整信息（+技术指标/估值数据） | ✅ 稳定 |

**重要发现**：tools/list 只返回 3 个工具。`industry_hot` 和 `LimitUp` 曾在 session 探索阶段出现，但不在工具列表中，属于 session 级临时工具，重置后消失。

## 替代方案

### 板块热点替代（实现方案）
- `industry_hot` → 用 `medium` 行业概念字段批量统计
- 已有 watchlist 中的股票，通过 medium 汇总行业概念分布
- 限制 5 只，避免超时；超时 5 秒/只
- 关键代码已写入 `morning_briefing.py` 的 `get_market_sectors()`

### 涨停股板块分布
- `LimitUp` → 无替代方案（MCP 无涨停池数据）
- 当前只能通过 `brief`/`medium` 逐一查询个股，无法批量获取涨停股

## 待探索（可选）
- [ ] `medium` 的 `main_net_inflow` 单位（亿 vs 万元，待验证）
- [ ] `full` 技术指标字段覆盖（MA5/10/30/60/120、KDJ、MACD、RSI、Bollinger）
