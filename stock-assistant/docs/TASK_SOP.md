# 每日 A 股操作 SOP（2026-03-27 建立）

## 一、开盘前（08:30 前）

### 08:30 自动任务
- [x] `morning_briefing.py` 自动生成早报
  - 数据源：MCP `brief`（持仓股）+ `industry_hot`（板块热点）+ push2（指数）
  - 输出：飞书推送 + `reports/daily-*.md`
  - 耗时：< 5 秒（MCP）

### 09:00 自动任务
- [x] `market_open_scan.py` 开盘扫描
  - 检查持仓股跳空/异动
  - 止损监控门控检查
  - 输出：飞书推送

## 二、盘中（09:00-15:00）

### 每小时半点
- [x] `stop_loss_monitor.py` 止损检查
  - 门控：`is_market_open()`（09:00-15:30）
  - 数据源：MCP `brief`
  - 告警去重：按浮亏比例（不含时间戳）
  - 配置：`data/alert_config.json`

### 持仓更新
- [x] `portfolio_monitor.py` 每小时更新
  - 数据源：MCP `brief`
  - 输出：`portal/status/portfolio.json`
  - 持仓历史：`portal/status/portfolio_history.json`

## 三、收盘后（16:00-16:30）

### 16:00 自动任务
- [x] `market_close_scan.py` 收盘报告生成
  - 数据源：MCP `brief`（持仓）+ push2（指数，今日恢复）
  - 输出：`reports/daily-close-YYYY-MM-DD.md`
  - 手动补发飞书（如自动推送失败）

### 每日复盘（可选）
- [x] `daily-growth-review` cron（22:00）
  - 持仓分析 + 选股复盘 + 学习复盘

## 四、数据源优先级

| 用途 | 主力 | 备用 | 状态 |
|------|------|------|------|
| 持仓股行情 | MCP `brief` | - | ✅ |
| 指数 | push2 + Referer | MCP `medium` | ✅ |
| 涨停股池 | push2（非贪婪解析） | - | ✅ |
| 资金流向 | MCP `medium` | - | ✅ |
| 板块热点 | MCP `industry_hot` | - | ⚠️ session不稳定 |
| K线历史 | MCP `full` | - | ✅ |
| 财务数据 | MCP `medium/full` | - | ✅ |

## 五、已知问题与应对

| 问题 | 级别 | 应对 |
|------|------|------|
| push2 无 Referer 会连接重置 | P2 | 始终加 `-H "Referer: https://quote.eastmoney.com/"` |
| industry_hot session 不稳定 | P2 | 失败时降级为"板块数据获取失败" |
| get_zt_pool f3=今日涨幅非昨日 | P2 | 注释已标注，选股需注意 |
| 300xxx 股票 MCP 需 SZ 前缀 | P1 | `normalize_symbol()` 已处理 |
| MCP push2 大整数字段需除100 | P1 | 已处理 |

## 六、Token 消耗规则（已纠正）

- API 字段 `current_interval_usage_count` = **剩余额度**（不是已用）
- 已用 = `total - usage_count`
- 停止线：已用 ≥ 80%（即剩余 ≤ 900）
- 当前剩余充足，本窗口可持续工作

### 板块热点替代方案（industry_hot 不可用时）
当 `industry_hot` session 不稳定时，用涨停股板块分布替代：
```python
# 涨停股板块分布（2026-03-27 示例）
国企改革: 10只 | 创新药: 5只(均13%) | 锂电池: 5只 | 医疗器械: 3只(均14%)
```
生成方式：`get_zt_pool()` → `normalize_symbol()` → `medium("行业概念")` → 统计
