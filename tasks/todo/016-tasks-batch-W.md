# 016 - 任务批次 W（2026-03-28 18:12 新规则后首批）

**Token**: A=3828, B=4500, remaining=3828(85.1%)
**Git**: clean，origin 已配置，等待 SSH key
**规则**: 飞书静默，过程写到文件，只在真正完成时通知

## W1: MCP 深度验证（高优先级）

- [ ] mcp_full_safe('605365') 验证返回完整数据
- [ ] mcp_medium('605365') 验证返回资金流向
- [ ] 测试 688xxx 科创板股票（多个）

## W2: stock_scan.py 批量扫描测试

- [ ] dry-run 测试（检查是否支持）
- [ ] 扫描前3只候选股
- [ ] 验证 KDJ/RSI/MA 输出

## W3: 系统自查

- [ ] 验证所有 cron 状态
- [ ] 检查 inbox_server 拉起机制
- [ ] 验证 backup 机制是否正常

## W4: GitHub SSH key（等待用户）

- [ ] 用户添加 SSH key 后执行首次 push
- [ ] 验证 push 成功

## W5: 文档完善

- [ ] 补充 MCP troubleshooting 到 docs/06
- [ ] 更新实施总文档 v2.2 最新变更
