#!/usr/bin/env python3
"""
market_research.py - 研究 Agent 任务：获取市场资讯和舆情
"""
import json
import subprocess
import os
from datetime import datetime

def main():
    print(f"=== 研究 Agent {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
    result = {}

    # 获取市场新闻
    try:
        import akshare as ak
        news = ak.stock_news_em(symbol="A股")
        if not news.empty:
            top_news = news.head(5)
            items = []
            for _, row in top_news.iterrows():
                items.append({
                    "title": str(row.get("标题",""))[:80],
                    "time": str(row.get("发布时间",""))[:16]
                })
            result["news"] = items
            print(f"新闻: {len(items)} 条")
    except Exception as e:
        print(f"新闻获取失败: {e}")
        result["news"] = []

    # 宏观数据
    try:
        gdp = ak.macro_china_gdp()
        result["macro"] = {
            "gdp_latest": str(gdp.iloc[-1])[:100] if not gdp.empty else None
        }
    except:
        result["macro"] = {}

    result["timestamp"] = datetime.now().isoformat()
    with open("/tmp/market-research-result.json", "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("研究数据已写入 /tmp/market-research-result.json")
    return result

if __name__ == "__main__":
    main()
