# 020 - 任务批次 Z（2026-03-28 19:30）

**Token**: A=3619, B=4500, remaining=3619(80.4%)
**Git**: clean

## Z1: 量化策略深化

- [ ] 扩展 tech_screen.py：增加 MACD 金叉/死叉检测
- [ ] 增加 MA 均线多头/空头排列判断
- [ ] 增加 BOLL 突破检测
- [ ] 测试多只候选股评分

## Z2: 文档完善

- [ ] `docs/06_股票业务规则.md` 补充技术指标选股标准
- [ ] `实施总文档_v2.2.md` 补充 tech_screen.py 工具说明
- [ ] `docs/CRON_CONFIG.md` 补充 tech_screen 在 cron 中的使用场景

## Z3: 候选股扫描

- [ ] 用 tech_screen.py 扫描 stock_pool 前5只股票
- [ ] 验证 KDJ 金叉检测效果
- [ ] 生成选股报告

## Z4: 系统自查

- [ ] 检查所有 scripts 是否还有潜在 bug
- [ ] 验证 stock_picker.py 逻辑
- [ ] 检查 alert_config.json 配置是否完整
