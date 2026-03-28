# 019 - 任务批次 Y（2026-03-28 19:25）

**Token**: A≈3668, B=4500, remaining≈3668(81.5%)
**Git**: clean
**状态**: GitHub阻塞，源码zip已就绪；其他工作正常

## Y1: 周一最终确认

- [ ] `market_open_scan.py --dry-run` 最终测试
- [ ] `stop_loss_monitor.py --dry-run` 最终测试
- [ ] `morning_briefing.py --dry-run` 最终测试
- [ ] 确认 inbox_server 拉起机制正常

## Y2: MCP 策略研究

- [ ] 基于 MCP full 数据设计选股策略
- [ ] 编写简单的技术指标选股函数
- [ ] 验证 KDJ 金叉/死叉检测

## Y3: 文档完善

- [ ] `docs/06` 补充 MCP full 数据结构说明
- [ ] `实施总文档_v2.2.md` 补充今日变更记录
- [ ] `TOOLS.md` 补充 MiniMax Coding Plan 查询命令

## Y4: 系统自查

- [ ] 验证所有 scripts 的 import 完整性
- [ ] 检查 `process_inbox.py` inbox_server 拉起逻辑
- [ ] 检查 `cron_health_check.py` 是否正常

## Y5: Clawhub 技能研究

- [ ] 访问 clawhub.ai 了解高价值技能
- [ ] 评估 `pdf`, `xlsx`, `docx` 技能适用性
- [ ] 评估 `weather`, `travel-planner` 技能适用性
