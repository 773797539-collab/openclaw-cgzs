# Event Dispatch Config
# main agent 读取此文件，决定如何处理各类 systemEvent

## 调度规则

| systemEvent | 调度动作 |
|-------------|----------|
| market-open-scan | main → spawn stock-exec → spawn stock-review → main notify |
| market-close-scan | main → spawn stock-exec → spawn stock-review → main notify |
| growth-review | main → spawn stock-learn → main notify |
| update-system-json | exec python3 scripts/update-system-json.py |
| update-portfolio-json | exec python3 scripts/update-portfolio-json.py |
| doc-export | exec bash stock-assistant/scripts/export-docs.sh |

## stock-exec 任务指令（JSON格式）

### market-open-scan
{
  "task": "执行每日开盘数据获取",
  "actions": [
    "获取上证/深成/创业板/科创50指数数据",
    "获取涨跌停数量统计",
    "读取data/watchlist.yaml获取持仓股",
    "查询各持仓股最新行情",
    "输出结构化数据到 /tmp/market-open-result.json"
  ],
  "output": "/tmp/market-open-result.json"
}

### market-close-scan
{
  "task": "执行每日收盘数据获取",
  "actions": [
    "获取各指数收盘数据",
    "统计涨跌停",
    "查询持仓股收盘行情",
    "输出到 /tmp/market-close-result.json"
  ],
  "output": "/tmp/market-close-result.json"
}

## stock-review 验收指令

### market-open-scan 验收
{
  "check": [
    "指数数据是否完整（4个指数都有值）",
    "涨跌停数量是否为有效数字",
    "持仓股数据是否包含现价/涨跌幅/成本/浮亏"
  ],
  "output": "/tmp/market-open-review.json"
}

## 执行超时
- stock-exec: 60秒
- stock-review: 30秒
- 超时视为失败，记录日志并通知用户数据获取超时
