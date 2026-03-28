# 008 - 下一批可执行任务（2026-03-28 17:04 生成）

**生成时间**: 2026-03-28 17:04
**状态**: todo
**来源**: 持续作业模式自动生成

---

## 任务池清单

### D1: 文档补全（立即可执行）
- [ ] `docs/05_OpenClaw更新与补丁日志.md` - 检查是否存在，缺失则从 TOOLS.md/AGENTS.md 提取 OpenClaw 版本历史
- [ ] `docs/04_技能插件来源与评估标准.md` - 检查是否完整，补充 clawhub.ai 技能评估标准
- [ ] 重建 `docs/04_验收闭环示例.md` - 如果内容过时

### D2: 脚本质量提升（立即可执行）
- [ ] `morning_briefing.py` - 添加 `--dry-run` 参数支持，方便测试
- [ ] `market_close_scan.py` - 添加输出文件路径参数化
- [ ] `stop_loss_monitor.py` - 添加 dry-run 测试模式

### D3: 数据管理（立即可执行）
- [ ] `candidate_scan_2026-03-28.json` - 检查内容质量，补充说明
- [ ] 候选股池质量报告生成（验证86只股票的数据完整性）
- [ ] `sector_watch.json` 转换为结构化持仓分析

### D4: workflow 验证（立即可执行）
- [ ] 验证 `market_open_scan.py` 周一 09:00 完整链路
- [ ] 验证 `market_close_scan.py` 飞书推送是否需要 app token 刷新
- [ ] 验证 `inbox_server.py` 是否正常监听 18790

### D5: 系统加固（立即可执行）
- [ ] 检查 OpenClaw cron 配置是否有遗漏的周日执行任务
- [ ] 验证 `git push` 是否正常工作（防止代码丢失）
- [ ] 备份策略检查：backups/ 保留策略（当前仅保留最新）

---

## 执行记录
- 2026-03-28 17:04: 生成本文档
- 待完成后逐项标记 done

---

## 已发现系统问题

### Git 无 Remote 配置
- **发现时间**: 2026-03-28 17:05
- **问题**: `git remote -v` 无输出，无 origin remote
- **影响**: 代码仅保存在本地，无远程备份
- **建议**: 添加 remote origin（需要用户提供 Git 仓库地址）

---

## 新发现的问题（17:05）

### Git 无 Remote 配置（严重）
- **问题**: `git remote -v` 无输出，无法 push
- **影响**: 代码仅本地，无远程备份
- **处置**: 放入审批池，待用户提供仓库地址

## E1-E3 已完成
- [x] E1 market_close_scan 飞书推送正常
- [x] E2 inbox 机制验证正常
- [x] E3 backups/README.md 新建

---

## G1-G6 执行记录
- [x] G2 docs/05 OpenClaw更新日志 ✅ (commit 352d4da)
- [x] G3 docs/07 技能插件（解决04编号冲突）✅ (commit d48d04b)
- [x] G4 04_验收闭环示例.md 无需更新 ✅
- [x] G5 event-dispatch.md 无需更新 ✅
- [x] G6 实施总文档20.4内容已完整 ✅

## D1-D5 执行记录
- [x] D1 docs/04新建+docs/05新建 ✅
- [x] D2 morning_briefing/market_close/stop_loss dry-run ✅
- [x] D3 stock_pool质量报告 ✅
- [x] D4 git push验证（发现无remote） ✅
- [x] D5 market_close飞书推送正常 ✅
