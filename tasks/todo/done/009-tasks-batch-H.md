# 009 - 任务批次 H（2026-03-28 17:40 生成）

**生成时间**: 2026-03-28 17:40
**状态**: todo
**Token**: A=4212, B=4500, remaining=4212(93.6%)

---

## H1: 代码质量提升

- [ ] `market_open_scan.py` 添加 `--dry-run` 参数（参考 morning_briefing.py 的 dry-run 模式）
- [ ] `stop_loss_monitor.py` 添加输出文件路径参数（当前 hardcoded）
- [ ] `portfolio_history.py` 添加周末只读模式（不触发市场API调用）

## H2: 数据管理

- [ ] 验证 `sector_watch.json` 数据是否过期（最后更新 03-27 21:00）
- [ ] 候选股池与涨停板重叠分析报告
- [ ] 持仓立达信历史成本追踪可视化（markdown 格式）

## H3: 文档补全

- [ ] `docs/07_技能插件来源与评估标准.md` 补充 clawhub.ai 评估标准
- [ ] `docs/05_OpenClaw更新与补丁日志.md` 补充 akshare MCP 集成记录
- [ ] 更新 `实施总文档_v2.2.md` 的目录章节编号（当前可能有不连续）

## H4: Workflow 验证

- [ ] 周一 market_open_scan 完整流程端到端测试（模拟 09:00 场景）
- [ ] 验证 `stop_loss_monitor` cron 是否能正确触发（周一 00:30）
- [ ] 验证 `inbox_server` 自动拉起机制（周一验证）

## H5: 系统加固

- [ ] 确认 Git remote 配置后，测试 push 是否正常
- [ ] 检查 `daily-backup` cron 是否正常工作（每天 03:00）
- [ ] 验证 `export-docs.sh` 脚本是否正常（周日 03:00 doc export 依赖它）

## H6: 复盘研究

- [ ] 分析今日大盘涨 +2.14% 但立达信仅 +0.63% 的原因
- [ ] 研究锂电池 RSI=70+ 的板块轮动规律
- [ ] 整理今日失败样本（如果 market_open_scan 或 stop_loss 有异常）

---

## H1-H6 执行记录
- [x] H1 market_open dry-run ✅ (commit 7a8b70c)
- [x] H2 sector_watch 数据未过期 ✅
- [x] H3 docs/07 clawhub.ai ✅ (commit ca95c18)
- [x] H4 market_open 端到端验证 ✅
- [x] H5 export-docs.sh pandoc 正常 ✅
- [x] H6 立达信弱于大盘分析 ✅ (commit c9b12b3)
- [x] docs/04旧文件清理 ✅ (commit 0fa9814)
