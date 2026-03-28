# stock-assistant - A股辅助决策系统

> 基于 OpenClaw 的 A股辅助决策工具，数据驱动，规则清晰，纯辅助不下单。

**项目状态**: 运营验证中（阶段3）
**创建时间**: 2026-03-26
**维护者**: OpenClaw Agent

---

## 快速开始

```bash
# 查看持仓实时状态
cd /home/admin/openclaw/workspace/stock-assistant
python3 scripts/portfolio_monitor.py

# 手动触发止损检查（交易时段）
python3 scripts/stop_loss_monitor.py

# 生成开盘前简报
python3 scripts/morning_briefing.py
```

---

## 核心功能

| 功能 | 说明 |
|------|------|
| 持仓监控 | 实时价格/成本/浮亏，MCP查询秒回 |
| 止损止盈 | 超线发飞书通知，不自动平仓 |
| 选股系统 | 强势股回调策略（仅交易时段有效） |
| 每日简报 | 08:30 推送飞书（含大盘/ETF/持仓/建议） |
| 盘后报告 | 每日收盘自动生成分析报告 |

---

## 数据源

- **MCP HTTP**: `http://82.156.17.205/cnstock/mcp`（主力）
- **东财 push2**: 备用指数接口
- **akshare**: 本地外网受限时不可用

---

## 目录结构

```
stock-assistant/
├── data/
│   ├── watchlist.yaml      # 持仓列表
│   ├── alert_config.json   # 止损止盈配置
│   └── alert_log.json      # 告警历史
├── scripts/
│   ├── mcp_stock.py        # MCP查询封装
│   ├── portfolio_monitor.py # 持仓监控
│   ├── stop_loss_monitor.py # 止损止盈
│   ├── stock_picker.py     # 选股系统
│   └── morning_briefing.py  # 每日简报
├── reports/                 # 每日报告存档
└── docs/                   # 文档
    ├── 06_股票业务规则.md  # 业务规则（新手必读）
    ├── 03_踩坑记录与失败样本.md
    └── 02_已验证有效命令与流程.md
```

---

## Portal

访问 `http://localhost:8081` 查看：
- 实时持仓市值和盈亏
- 任务池状态
- 系统健康状态
- 持仓历史曲线

---

## 注意事项

- 系统**不连接券商接口**，不执行任何买卖委托
- 所有建议仅供参考，决策权始终在人工
- Token 消耗规则：未达 80% 之前必须持续工作，不允许空闲

---

## 关键操作命令

### MCP 股票查询（必须 normalize）
```python
from mcp_utils import mcp_brief, normalize_symbol
text = mcp_brief(normalize_symbol('605365'))  # ✅
text = mcp_brief('605365')  # ❌ 返回空
```

### 止损监控
```bash
# 手动运行（交易时段）
python3 scripts/stop_loss_monitor.py

# 测试模式
python3 scripts/stop_loss_monitor.py --dry-run
```

### 开盘扫描
```bash
python3 scripts/market_open_scan.py --dry-run
```

### MCP 健康检查
```python
from mcp_utils import mcp_health_check
ok, ms, err = mcp_health_check()
```

### Portal 重启
```bash
pkill -f "python3 server.py" && cd portal && nohup python3 server.py > /tmp/portal.log 2>&1 &
```

### Token 查询
```bash
curl -s 'https://www.minimaxi.com/v1/api/openplatform/coding_plan/remains' \
  -H 'Authorization: Bearer <MINIMAX_API_KEY_REVOKED>'
```

### MCP 故障排查
见 `docs/MCP_troubleshooting.md`
