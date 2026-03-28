# 013 - 任务批次 N（2026-03-28 17:58 生成）

**生成时间**: 2026-03-28 17:58
**状态**: todo
**Token**: A=3992, B=4500, remaining=3992(88.7%)

---

## N1: 代码质量复查

- [ ] `mcp_utils.py` - 检查是否有重复代码
- [ ] `stock_picker.py` - 是否有死代码或冗余函数
- [ ] `update-system-json.py` - 是否覆盖了 tasks.json（应只更新 system.json）

## N2: 文档完善

- [ ] `docs/CRON_CONFIG.md` - 检查是否需要更新
- [ ] `docs/TASK_FLOW.md` - 验证是否与当前工作流一致
- [ ] `stock-assistant/README.md` - 是否存在，内容是否需要更新

## N3: 验证脚本dry-run

- [ ] `morning_briefing.py --dry-run` 测试（检查是否支持）
- [ ] `portfolio_monitor.py --dry-run` 测试
- [ ] `market_sectors.py --dry-run` 测试

## N4: 数据文件清理

- [ ] `candidate_pool.json` - 检查是否有重复记录
- [ ] `alert_log.json` - 检查是否有异常告警记录
- [ ] `watchlist.json` - 格式是否正确

## N5: Git 远程配置（阻塞）

- [ ] 等待用户提供 Git 仓库地址
- [ ] 配置 remote 并首次 push

## N6: 周一最终准备

- [ ] 确认 market_open_scan cron 已配置（09:00 周一至周五）
- [ ] 确认 stop_loss_monitor cron 已配置（每30分钟）
- [ ] 准备周一开盘前飞书通知
