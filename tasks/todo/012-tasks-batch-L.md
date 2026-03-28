# 012 - 任务批次 L（2026-03-28 17:50 生成）

**生成时间**: 2026-03-28 17:50
**状态**: todo
**Token**: A=4153, B=4500, remaining=4153(92.3%)

---

## L1: 代码质量提升（续）

- [ ] `market_close_scan.py` - 添加 --dry-run 参数（当前只有 main）
- [ ] `portfolio_monitor.py` - 检查是否有错误处理
- [ ] `market_sectors.py` - 检查是否有冗余/死代码

## L2: 文档完善

- [ ] `docs/02_已验证有效命令与流程.md` - 检查是否需要更新
- [ ] `docs/07_技能插件来源与评估标准.md` - 补充最新已安装技能
- [ ] 更新 `docs/01_当前环境与版本清单.md` 最新 commit

## L3: 数据管理

- [ ] `candidate_scan.json` - 补充说明字段含义
- [ ] `alert_log.json` - 告警触发频率统计
- [ ] sector_watch.json 与候选股池重叠分析

## L4: 系统加固

- [ ] Portal API 无响应问题排查（重启方案）
- [ ] `cron_health_check.py` - 添加磁盘空间检查
- [ ] 验证 `openclaw gateway restart` 是否能恢复 Portal

## L5: 复盘总结

- [ ] 编写今日（周六）工作总结
- [ ] 更新 `memory/2026-03-28.md` 最新进展
- [ ] 更新 `HEARTBEAT.md` 持续作业进展

## L6: 周一最终确认

- [ ] `stop_loss_monitor.py --dry-run` 最终测试
- [ ] `market_open_scan.py --dry-run` 最终测试
- [ ] 确认 inbox_server 是否正常（周一验证）
