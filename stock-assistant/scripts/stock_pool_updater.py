#!/usr/bin/env python3
"""
stock_pool_updater.py - 每日收盘后自动更新涨停候选池
cron: 16:05 周一至周五
将涨停股存入 POOL_FILE，作为次日选股候选池
"""
import sys, os, json
from datetime import datetime

sys.path.insert(0, '/home/admin/openclaw/workspace/stock-assistant/scripts')
from stock_picker import get_zt_pool, get_prices_concurrent, POOL_FILE

POOL_FILE = "/home/admin/openclaw/workspace/stock-assistant/data/stock_pool.json"

def update_pool():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 更新涨停候选池...")
    zt = get_zt_pool()
    if not zt:
        print("涨停池为空，跳过")
        return
    
    # 获取实时价格补充
    codes = [s["code"] for s in zt]
    prices = get_prices_concurrent(codes)
    
    # 合并数据
    pool = []
    for s in zt:
        info = prices.get(s["code"], {})
        pool.append({
            "code": s["code"],
            "name": s.get("name", info.get("name", "")),
            "pct": s["pct"],          # 当日涨停幅度（f3=今日涨幅，非昨日）
            "turnover": s.get("turnover"),
            "amplitude": s.get("amplitude"),
            "price": info.get("price"),
            "实时涨跌幅": info.get("pct", 0),
        })
    
    # 保存
    os.makedirs(os.path.dirname(POOL_FILE), exist_ok=True)
    with open(POOL_FILE, "w") as f:
        json.dump({"stocks": pool, "last_update": datetime.now().strftime("%Y-%m-%d %H:%M")}, f, ensure_ascii=False, indent=2)
    
    print(f"候选池已更新: {len(pool)} 只，存入 {POOL_FILE}")
    # 打印换手率前5
    top5 = sorted(pool, key=lambda x: x.get("turnover") or 0, reverse=True)[:5]
    print("换手率Top5:")
    for s in top5:
        print(f"  {s['name']}({s['code']}): 换手{s.get('turnover','?')}%  当日涨停{s['pct']}%")

if __name__ == "__main__":
    update_pool()
