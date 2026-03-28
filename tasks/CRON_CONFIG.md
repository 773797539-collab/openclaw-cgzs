# Cron 任务配置

**最后更新**: 2026-03-28 04:25

## 查看方式
```bash
openclaw cron list
```

---

## 定时任务清单（openclaw cron list 实测）

| 任务ID | 名称 | 时间 | 状态 | 上次运行 |
|--------|------|------|------|----------|
| 084bbaeb | daily-backup | 03:00 每天 | ok | 约1小时前 |
| - | weekly-doc-export | 03:00 每周日 | idle | - |
| - | daily-morning-briefing | 08:30 周一至周五 | ok | 约20小时前 |
| - | daily-market-open-scan | 09:00 周一至周五 | ok | 约19小时前 |
| - | daily-market-close-scan | 16:00 周一至周五 | ok | 约12小时前 |
| - | daily-growth-review | 22:00 每天 | - | - |

## 脚本对应

| cron 任务 | 实际脚本 | 飞书通知 | 非交易日保护 |
|------------|----------|----------|-------------|
| daily-morning-briefing | `morning_briefing.py` | ✅ | ✅ `can_run()` |
| daily-market-open-scan | `market_open_scan.py` | ❌ | cron周一至周五 |
| daily-market-close-scan | `market_close_scan.py` | ✅ | cron周一至周五 |
| daily-growth-review | - | ❌ | - |
| stop_loss_monitor | `stop_loss_monitor.py` | ✅ cron f2b67233（周一至周五 半点）| ✅ `is_market_open()` |

## 系统级任务（crontab）

| 任务 | 时间 | 脚本 | 说明 |
|------|------|------|------|
| cloudflared | */5 分钟 | /tmp/restart_cf.sh | 确保隧道运行 |
| portal runner | * * * * * | /tmp/portal_runner.sh | 确保 Portal 运行 |

## 注意事项

- `stop_loss_monitor.py` 有 `is_market_open()` 保护（09:00-15:30，周一至周五）
- `morning_briefing.py` 有 `can_run()` 保护（非交易时段+周末退出）
- `stock_scan.py` 有 `can_scan()` 保护（非交易时段+周末退出）
- 止损告警已实现去重（基于浮亏比例）
- MCP 为主要数据源，非交易时段可查询持仓数据
