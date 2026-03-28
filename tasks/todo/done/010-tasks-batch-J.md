# 010 - 任务批次 J（2026-03-28 17:15 生成）

**生成时间**: 2026-03-28 17:15
**状态**: todo
**Token**: A=4167, B=4500, remaining=4167(92.6%)

---

## J1: 脚本健壮性提升

- [ ] `portfolio_history.py` - 检查是否有错误处理（网络超时/JSON解析失败）
- [ ] `mcp_stock.py` - 添加 retry 机制（网络抖动时自动重试）
- [ ] `stock_scan.py` - 添加 `--json` 输出参数，方便程序化使用

## J2: 数据可视化（Markdown格式）

- [ ] 持仓立达信历史走势图（ASCII表格）
- [ ] 候选股池价格分布直方图（ASCII柱状图）
- [ ] 板块 RSI 健康度汇总表

## J3: 通知链路优化

- [ ] 检查飞书通知是否有失败重试机制
- [ ] 告警消息格式优化（emoji + 关键信息突出）
- [ ] 通知频率限制（防止同一问题重复推送）

## J4: 文档补全

- [ ] `docs/01_当前环境与版本清单.md` - 更新最后检查时间
- [ ] `docs/02_已验证有效命令与流程.md` - 检查是否需要补充
- [ ] 更新 `实施总文档_v2.2.md` 章节编号检查（04+07冲突已解决）

## J5: 运维自动化

- [ ] `clean_old_logs.py` - 验证是否能正确清理 N 天前日志
- [ ] `cron_health_check.py` - 添加 `--json` 输出，方便程序化调用
- [ ] 备份验证：解压一个 backup.tar.gz 确认内容完整

## J6: 周一准备最终确认

- [ ] 再次验证 market_open_scan 周一 09:00 触发链路
- [ ] 验证 stop_loss_monitor cron 状态
- [ ] 生成周一开盘前最终检查清单

---

## J1-J6 执行记录
- [x] J1-1 portfolio_history 错误处理 ✅ (commit 52460c7)
- [x] J1-2 mcp_stock retry 机制 ✅ (commit 123b0aa)
- [x] J1-3 stock_scan --json + dry-run + datetime修复 ✅ (commit 4d03167)
- [x] J2 持仓走势图 ✅ (commit 4d03167)
- [x] J3 飞书重试机制（基础正常，无需修改） ✅
- [x] J4 docs/01 更新 ✅ (commit 7a5e37f)
- [x] J5-2 cron_health_check --json ✅ (commit f9f1f2a)
- [x] J5-3 备份验证 ✅（4483文件完整）
- [x] J6 market_open_scan 触发链路 ✅（周一起源09:00，状态ok）
