# CRON_CONFIG.md - 定时任务配置清单

**最后更新**: 2026-03-28 19:15

---

## 一、定时任务列表

| 任务名 | 调度规则 | 说明 | 状态 |
|--------|----------|------|------|
| daily-backup | `0 3 * * *` | 每日03:00备份 | ✅ ok |
| weekly-doc-export | `0 3 * * 0` | 每周日03:00导出文档 | ✅ idle |
| daily-morning-briefing | `30 8 * * 1-5` | 工作日08:30生成简报 | ✅ ok |
| daily-market-open-scan | `0 9 * * 1-5` | 工作日09:00开盘扫描 | ✅ ok |
| daily-market-close-scan | `0 16 * * 1-5` | 工作日16:00收盘扫描 | ✅ ok |
| daily-market-open-scan | `0 9 * * 1-5` | 工作日09:00开盘扫描 | ✅ ok |
| hourly-stop-loss-monitor | `30 * * * 1-5` | 工作日每30分钟止损监控 | ✅ idle |

---

## 二、任务详情

### daily-morning-briefing
- **命令**: `openclaw cron run daily-morning-briefing`
- **用途**: 生成A股开盘前简报，推送飞书
- **输入**: watchlist + 持仓数据 + MCP
- **输出**: 飞书消息 + reports/morning-briefing-YYYY-MM-DD.md
- **下次触发**: 周一 08:30

### daily-market-open-scan
- **命令**: `openclaw cron run daily-market-open-scan`
- **用途**: 开盘扫描持仓股+候选股
- **输入**: portfolio.json + stock_pool.json
- **输出**: reports/market-open-YYYY-MM-DD.md
- **下次触发**: 周一 09:00

### daily-market-close-scan
- **命令**: `openclaw cron run daily-market-close-scan`
- **用途**: 收盘报告生成
- **输入**: MCP push2 实时数据
- **输出**: reports/daily-close-YYYY-MM-DD.md
- **下次触发**: 周一 16:00

### hourly-stop-loss-monitor
- **命令**: `openclaw cron run hourly-stop-loss-monitor`
- **用途**: 持仓股止损/止盈监控
- **输入**: portfolio.json + alert_config.json
- **输出**: 飞书告警（如触发）
- **触发条件**: 浮亏超15% 或 浮盈超20%
- **下次触发**: 周一 09:30

### daily-backup
- **命令**: `openclaw cron run daily-backup`
- **用途**: 备份 workspace 到 tar.gz
- **输出**: `backups/YYYY-MM-DD...-openclaw-backup.tar.gz`
- **下次触发**: 明日 03:00

### weekly-doc-export
- **命令**: `openclaw cron run weekly-doc-export`
- **用途**: 导出实施总文档为 DOCX
- **输出**: `exports/实施总文档_YYYYMMDD.docx`
- **下次触发**: 周日 03:00

---

## 三、cron 常用命令

```bash
# 列出所有 cron 任务
openclaw cron list

# 查看特定任务状态
openclaw cron status <任务ID>

# 手动触发任务
openclaw cron run <任务名>

# 查看任务执行历史
openclaw cron history <任务ID>

# 查看最近执行结果
openclaw cron list --long
```

---

## 四、注意事项

1. **周末**: 所有市场相关 cron 不运行（周一至周五）
2. **inbox_server**: 由 `process_inbox` 自动拉起，不在 cron 中配置
3. **Portal**: 需要手动启动（`python3 server.py`），进程挂了不会自动重启
4. **Token 监控**: 通过 HEARTBEAT.md 每10分钟检查，不单独配置 cron
