#!/usr/bin/env python3
"""生成持仓数据 JSON，供门户页动态展示"""
import json
import os
import subprocess
from datetime import datetime

PORTFOLIO_JSON = "/home/admin/openclaw/workspace/portal/status/portfolio.json"
WATCHLIST = "/home/admin/openclaw/workspace/stock-assistant/data/watchlist.yaml"

def get_stock_price(code):
    """通过 finance-data skill 获取股价"""
    try:
        result = subprocess.run(
            ["bash", os.path.expanduser("~/.openclaw/skills/finance-data/tools/query.sh"), "info", code.strip()],
            capture_output=True, text=True, timeout=10
        )
        data = json.loads(result.stdout)
        if data.get("type") == "stock":
            d = data.get("data", {})
            return {
                "price": d.get("price"),
                "change_pct": d.get("change_pct"),
                "name": data.get("name")
            }
    except:
        pass
    return None

def main():
    # 读 watchlist
    holdings = []
    cost_map = {}
    
    if os.path.exists(WATCHLIST):
        with open(WATCHLIST) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # 先去掉尾部注释，再解析
                code_part = line.split("#")[0].strip()
                parts = code_part.split()
                if parts:
                    code = parts[0]
                    # 格式支持:
                    # 新格式: 代码 股数 成本 (如 "605365 100 20.655")
                    # 旧格式: 代码 成本 (如 "605365 20.655")
                    # 注释兜底: "# 立达信，成本价 20.655"
                    import re
                    if len(parts) >= 3:
                        qty = int(parts[1])
                        cost = float(parts[2])
                    elif len(parts) == 2:
                        qty = 100  # 默认股数
                        cost = float(parts[1])
                    else:
                        qty, cost = 100, None
                    # 兜底：从注释提取
                    if cost is None and "#" in line:
                        comment = line.split("#")[1]
                        m = re.search(r'(\d+\.?\d*)', comment)
                        if m:
                            cost = float(m.group(1))
                    info = get_stock_price(code)
                    if info:
                        cur_price = info.get("price")
                        change = info.get("change_pct")
                        profit_pct = None
                        if cost and cur_price:
                            profit_pct = round((cur_price - cost) / cost * 100, 2)
                        holdings.append({
                            "code": code,
                            "name": info.get("name"),
                            "price": cur_price,
                            "change_pct": change,
                            "cost": cost,
                            "qty": qty,
                            "profit_pct": profit_pct
                        })
                        cost_map[code] = cost
    
    # 计算 summary
    summary = {}
    if holdings and all(h.get('cost') and h.get('price') for h in holdings):
        total_cost = sum(h['cost'] * h['qty'] for h in holdings)
        total_value = sum(h['price'] * h['qty'] for h in holdings)
        total_profit = round(total_value - total_cost, 2)
        total_profit_pct = round(total_profit / total_cost * 100, 2)
        today_pct = holdings[0].get('change_pct', 0)
        summary = {
            "total_profit": total_profit,
            "total_profit_pct": total_profit_pct,
            "today_profit_pct": today_pct
        }
    
    result = {
        "lastUpdated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "holdings": holdings,
        "summary": summary
    }
    
    with open(PORTFOLIO_JSON, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 持仓数据已更新: {len(holdings)} 只股票")

if __name__ == "__main__":
    main()
