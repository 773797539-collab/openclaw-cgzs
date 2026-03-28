# 流程与模板层 - stock-assistant

**层级**: 第二层 - 流程与模板
**说明**: SOP、命令模板、结果模板、复盘模板、通知模板

---

## 一、股票信息查询 SOP

```bash
# 1. 搜索股票代码（如需要）
bash ~/.openclaw/skills/finance-data/tools/query.sh search "股票名称"

# 2. 获取股票信息
bash ~/.openclaw/skills/finance-data/tools/query.sh info 600000

# 3. 获取历史数据
bash ~/.openclaw/skills/finance-data/tools/query.sh history 600000 30

# 4. 获取市场新闻
bash ~/.openclaw/skills/finance-data/tools/query.sh market-news 5
```

---

## 二、每日报告生成 SOP

1. 获取持仓列表
2. 获取每只持仓股当日数据
3. 获取市场概况
4. 生成报告 Markdown
5. 保存到 `reports/`

---

## 三、通知格式模板

```
【类型】标题
结论
详情
---
来源: stock-assistant
时间: {timestamp}
```

---

## 四、更新记录

| 日期 | 更新内容 |
|------|----------|
| 2026-03-26 | 初始化流程与模板层 |
