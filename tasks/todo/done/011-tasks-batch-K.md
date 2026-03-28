# 011 - 任务批次 K（2026-03-28 17:35 生成）

**生成时间**: 2026-03-28 17:35
**状态**: todo
**Token**: A=4167, B=4500, remaining=4167(92.6%)

---

## K1: 脚本健壮性（续）

- [ ] `stop_loss_monitor.py` - 添加输出路径参数化（`--config` 参数）
- [ ] `stock_scan.py` - 添加并发扫描（当前串行，速度慢）
- [ ] `inbox_server.py` - 检查是否有超时设置（防止挂起）

## K2: 文档完善

- [ ] `docs/03_踩坑记录与失败样本.md` - 追加今天发现的新踩坑
- [ ] `docs/06_股票业务规则.md` - 补充涨跌停规则详细说明
- [ ] 验证 `实施总文档_v2.2.md` 的章节编号连续性

## K3: 数据管理

- [ ] `candidate_scan.json` 转换为 `候选股池质量报告` Markdown
- [ ] sector_watch.json 数据结构分析（是否为最后更新时间？）
- [ ] alert_log.json 告警历史分析（有多少次触发？）

## K4: Workflow 优化

- [ ] `market_close_scan.py` 飞书消息格式优化（加入更多 emoji）
- [ ] `morning_briefing.py` - 添加持仓重点摘要章节
- [ ] `stop_loss_monitor.py` - 添加"连续告警"检测（防抖动）

## K5: 系统加固

- [ ] 验证所有脚本的 `if __name__ == "__main__"` 都有 dry-run 支持
- [ ] `clean_old_logs.py` - 检查是否有清理间隔配置（避免频繁清理）
- [ ] Portal health API 延迟测试（测量实际响应时间）

## K6: 复盘研究

- [ ] 分析过去3天大盘走势与持仓立达信的相关性
- [ ] 研究上证指数技术信号（MA5/MA20 金叉？RSI？）
- [ ] 整理今日（周六）所有发现的问题清单
