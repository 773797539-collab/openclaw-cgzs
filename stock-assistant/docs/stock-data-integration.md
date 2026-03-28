# 股票数据集成 - stock-assistant

**版本**: v1.0
**更新时间**: 2026-03-26 02:58 GMT+8

---

## 一、数据源

| 数据源 | 用途 | 状态 |
|--------|------|------|
| akshare (Python) | A股、港股、基金、宏观数据 | ✅ 已安装 (v1.18.38) |
| finance-data skill | 封装查询工具 | ✅ 已配置 |
| MiniMax API | 模型分析 | ✅ 已配置 |

---

## 二、可用查询命令

```bash
# 股票信息（价格+指标）
bash ~/.openclaw/skills/finance-data/tools/query.sh info 600000

# 市场新闻
bash ~/.openclaw/skills/finance-data/tools/query.sh market-news 5

# 搜索股票
bash ~/.openclaw/skills/finance-data/tools/query.sh search "股票名称"

# 历史价格
bash ~/.openclaw/skills/finance-data/tools/query.sh history 600000 30

# 财务报告
bash ~/.openclaw/skills/finance-data/tools/query.sh financial 600519
```

---

## 三、集成方式

通过 Python 直接调用 akshare：

```python
import akshare as ak

# 实时行情
df = ak.stock_zh_a_spot_em()

# 个股信息
df = ak.stock_individual_info_em(symbol="600000")

# 财务指标
df = ak.stock_financial_analysis_indicator(symbol="600000", start_year="2024")
```

---

## 四、数据延迟

- 实时数据：15分钟延迟
- 财务数据：季度更新
- 公告：当日更新

---

## 五、已验证功能

| 功能 | 状态 | 备注 |
|------|------|------|
| A股实时价格 | ✅ | 浦发银行测试通过 |
| 市场新闻 | ✅ | 财新网数据 |
| 股票搜索 | ⚠️ | 超时，疑似网络问题 |
| 历史数据 | 待测 | - |
| 财务数据 | 待测 | - |

---

## 六、下一步

1. 验证历史价格查询
2. 建立持仓跟踪数据结构
3. 实现定时报告生成
