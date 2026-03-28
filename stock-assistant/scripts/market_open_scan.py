#!/usr/bin/env python3
"""
每日开盘扫描脚本
使用 MCP + 东财 push2 API，不再依赖 akshare
"""
import sys, os, json, subprocess, re, urllib.request
from datetime import datetime

sys.path.insert(0, '/home/admin/openclaw/workspace/stock-assistant/scripts')
from mcp_stock import get_stock_info

WATCHLIST = "/home/admin/openclaw/workspace/stock-assistant/data/watchlist.yaml"
PORTFOLIO = "/home/admin/openclaw/workspace/portal/status/portfolio.json"

# 东财 push2 秒级指数查询
def get_index(secid):
    """secid格式: 1.000001(上证) 0.399001(深成) 0.399006(创业板) 1.000688(科创50)"""
    url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields=f43,f57,f58,f170,f171"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        d = json.loads(resp.read()).get("data", {})
        price = d.get("f43", 0) / 100
        pct = d.get("f170", 0) / 100
        name = d.get("f58", secid)
        vol = d.get("f171", 0)
        return {"name": name, "price": price, "pct": pct, "secid": secid}

def read_watchlist_codes():
    codes = []
    if os.path.exists(WATCHLIST):
        with open(WATCHLIST) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                code = line.split("#")[0].strip().split()[0]
                codes.append(code)
    return codes

def main():
    print(f"执行开盘扫描 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 主要指数
    indices = [
        ("上证指数", "1.000001"),
        ("深证成指", "0.399001"),
        ("创业板指", "0.399006"),
        ("科创50", "1.000688"),
    ]
    print("【大盘概览】")
    for name, secid in indices:
        try:
            idx = get_index(secid)
            sign = "+" if idx["pct"] >= 0 else ""
            emoji = "🟢" if idx["pct"] > 0 else ("🔴" if idx["pct"] < 0 else "⚪")
            print(f"  {emoji} {name}: {idx['price']} ({sign}{idx['pct']:.2f}%)")
        except Exception as e:
            print(f"  ❓ {name}: 获取失败 ({e})")
    print()

    # 持仓股状态
    portfolio_holdings = []
    if os.path.exists(PORTFOLIO):
        with open(PORTFOLIO) as f:
            d = json.load(f)
            portfolio_holdings = d.get("holdings", [])

    if portfolio_holdings:
        print("【持仓监控】")
        for h in portfolio_holdings:
            code = h.get("code")
            try:
                info = get_stock_info(code)
                if info and info.get("price"):
                    pct = info.get("change_pct", 0)
                    cost = h.get("cost", 0)
                    price = info["price"]
                    profit_pct = (price - cost) / cost * 100 if cost else 0
                    sign1 = "+" if pct >= 0 else ""
                    sign2 = "+" if profit_pct >= 0 else ""
                    print(f"  {info.get('name','?')}({code}): ¥{price} {sign1}{pct:.2f}% | 成本¥{cost} {sign2}{profit_pct:.1f}%")
                else:
                    print(f"  {h.get('name','?')}({code}): 现价获取失败")
            except Exception as e:
                print(f"  {h.get('name','?')}({code}): 查询异常 ({e})")
        print()
    else:
        print("【持仓】无持仓数据\n")

    # 自选股扫描
    codes = read_watchlist_codes()
    if codes:
        print(f"【关注列表】共 {len(codes)} 只")
        for code in codes[:10]:
            try:
                info = get_stock_info(code)
                if info and info.get("price"):
                    pct = info.get("change_pct", 0)
                    sign = "+" if pct >= 0 else ""
                    print(f"  {info.get('name','?')}({code}): ¥{info['price']} {sign}{pct:.2f}%")
            except:
                pass
        print()

    print(f"扫描完成 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    import sys
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    if dry_run:
        print("=== market_open_scan dry-run 模式 ===")
        print(f"当前: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"交易日: {datetime.now().weekday() < 5}")
        print("（实际执行开盘扫描，生成报告，推送飞书）")
        sys.exit(0)
    elif datetime.now().weekday() >= 5:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 今日非交易日，跳过开盘扫描")
        exit(0)
    else:
        main()
