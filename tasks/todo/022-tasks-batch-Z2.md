# 022 - 任务批次 Z+2（2026-03-28 20:00）

**Token**: A≈3619, B=4500, remaining≈3619(80.4%)
**Git**: clean, latest commit 95c09dd

## Z+2-1: MCP 量化策略

- [ ] 验证立达信(605365)止损计算：BOLL Lower ¥16.49，止损 ¥16.49
- [ ] 验证止损距当前价格空间（¥18.35 vs ¥16.49 = -10.1%）
- [ ] MCP full 数据中提取 BOLL 支撑位

## Z+2-2: 文档完善

- [ ] `docs/MCP_troubleshooting.md` 补充 Mermaid 图表
- [ ] `docs/04_验收闭环示例.md` 追加 tech_screen 闭环记录
- [ ] `docs/06` 补充 BOLL 止损计算公式

## Z+2-3: 候选股池分析

- [ ] 分析 688197 首药控股-U 为何评分最高
- [ ] 验证该股是否值得加自选

## Z+2-4: 系统自查

- [ ] 验证 `process_inbox.py` inbox_server 拉起机制（已确认正常）
- [ ] 验证 `cron_health_check.py` 是否正常
- [ ] 验证 GitHub remote 配置

## Z+2-5: 研究

- [ ] 调研 `clawhub.ai` 高价值技能
- [ ] 评估 MCP push2 实时数据接入方案
