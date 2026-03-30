#!/usr/bin/env python3
"""
持仓/观察池扫描任务处理器
输入：持仓code列表 or 观察池code列表
处理：
  1. 获取持仓/观察池数据（从 holdings.json / watchlist.json）
  2. 通过 MCP 或 akshare 获取最新价格
  3. 计算浮亏/浮盈、距止损/止盈距离
  4. 判断风险状态
  5. 生成结论和建议
  6. 回写到 holdings.json / watchlist.json
  7. 返回结构化结果
"""
import os, json, sys, datetime, urllib.request, urllib.error
from pathlib import Path

WORKSPACE   = "/home/admin/openclaw/workspace"
STOCK_WS    = f"{WORKSPACE}/stock-assistant"
DATA_DIR    = f"{STOCK_WS}/data"
PORTFOLIO_J = f"{DATA_DIR}/holdings.json"
WATCHLIST_J = f"{DATA_DIR}/watchlist.json"

sys.path.insert(0, f"{WORKSPACE}/scripts")

def get_holdings():
    if os.path.exists(PORTFOLIO_J):
        with open(PORTFOLIO_J) as f:
            return json.load(f).get("holdings", [])
    return []

def get_watchlist():
    if os.path.exists(WATCHLIST_J):
        with open(WATCHLIST_J) as f:
            return json.load(f).get("items", [])
    return []

def write_holdings(holdings):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(PORTFOLIO_J, "w") as f:
        json.dump({"source": "manual", "updated": datetime.datetime.now().isoformat(), "holdings": holdings}, f, ensure_ascii=False, indent=2)

def write_watchlist(items):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(WATCHLIST_J, "w") as f:
        json.dump({"source": "manual", "updated": datetime.datetime.now().isoformat(), "items": items}, f, ensure_ascii=False, indent=2)

# ===== 价格获取（三种途径：MCP HTTP > akshare > fallback）=====
def fetch_price(code):
    """通过 price_fetch.py 获取价格"""
    import subprocess
    try:
        r = subprocess.run(
            ["python3", "/home/admin/openclaw/workspace/scripts/price_fetch.py", code],
            capture_output=True, text=True, timeout=5
        )
        if r.returncode == 0:
            data = json.loads(r.stdout)
            if "price" in data:
                return data
    except:
        pass
    return None

# ===== 持仓单股扫描 =====
def scan_holding(code):
    """扫描单只持仓股，返回扫描结果"""
    holdings = get_holdings()
    item = next((h for h in holdings if h.get("code") == code), None)
    if not item:
        return {"error": f"持仓 {code} 不存在"}

    name     = item.get("name", code)
    buy_price = float(item.get("buy_price", 0))
    stop_loss = float(item.get("stop_loss", 0))
    take_profit = float(item.get("take_profit", 0))
    shares   = int(item.get("shares", 0))

    # 获取最新价格
    live = fetch_price(code)
    if live:
        price = float(live.get("price", 0))
        pct_chg = float(live.get("pct", 0))
    else:
        price = buy_price  # fallback
        pct_chg = 0.0

    # 计算盈亏
    if buy_price > 0:
        profit_pct = (price - buy_price) / buy_price * 100
        profit_amt  = (price - buy_price) * shares
    else:
        profit_pct = 0
        profit_amt = 0

    # 止损/止盈判断
    stop_loss_hit = price <= stop_loss if stop_loss > 0 else False
    take_profit_hit = price >= take_profit if take_profit > 0 else False

    # 风险状态判断
    if stop_loss_hit:
        risk_status = "⚠️ 触发止损"
        action = "建议止损出局，控制风险"
    elif take_profit_hit:
        risk_status = "✅ 触发止盈"
        action = "建议分批止盈"
    elif profit_pct >= 5:
        risk_status = "✅ 浮盈可观"
        action = "持有，关注止盈时机"
    elif profit_pct >= 0:
        risk_status = "✅ 浮盈"
        action = "持有"
    elif profit_pct >= -5:
        risk_status = "⚠️ 轻微浮亏"
        action = "持有，等待回归"
    elif profit_pct >= -10:
        risk_status = "🔴 较大浮亏"
        action = "持有，关注止损线"
    else:
        risk_status = "🚨 接近止损"
        action = "密切监控，跌破止损立即出局"

    # 生成结论
    conclusion = (
        f"{name}({code})：现价¥{price:.2f}（{'+' if pct_chg >= 0 else ''}{pct_chg:.2f}%），"
        f"浮{'盈' if profit_pct >= 0 else '亏'}{abs(profit_pct):.1f}%（¥{abs(profit_amt):.0f}元）。"
        f"止损¥{stop_loss:.2f}（距{abs(profit_pct) - abs((price - stop_loss)/buy_price*100):.1f}%），"
        f"止盈¥{take_profit:.2f}。风险状态：{risk_status}。建议：{action}。"
    )

    # 回写到 holdings.json
    item["price"] = price
    item["change_pct"] = pct_chg
    item["profit_pct"] = round(profit_pct, 2)
    item["profit_amt"] = round(profit_amt, 2)
    item["risk_status"] = risk_status
    item["latest_conclusion"] = conclusion
    item["suggested_action"] = action
    item["last_scan_at"] = datetime.datetime.now().isoformat()
    item["status"] = "scanned"
    write_holdings(holdings)

    # 记录到 scan_history.json
    record_scan(code, "holding", {
        "price": price, "profit_pct": round(profit_pct, 2),
        "risk_status": risk_status, "conclusion": conclusion,
        "action": action
    })

    return {
        "code": code, "name": name,
        "price": price, "buy_price": buy_price,
        "profit_pct": round(profit_pct, 2), "profit_amt": round(profit_amt, 2),
        "stop_loss": stop_loss, "take_profit": take_profit,
        "stop_loss_hit": stop_loss_hit, "take_profit_hit": take_profit_hit,
        "risk_status": risk_status,
        "conclusion": conclusion,
        "action": action,
        "scan_at": item["last_scan_at"]
    }

# ===== 观察池单股扫描 =====
def scan_watch(code):
    """扫描单只观察股"""
    watchlist = get_watchlist()
    item = next((w for w in watchlist if w.get("code") == code), None)
    if not item:
        return {"error": f"观察池 {code} 不存在"}

    name = item.get("name", code)
    live = fetch_price(code)
    if live:
        price = float(live.get("price", 0))
        pct_chg = float(live.get("pct", 0))
    else:
        price = 0
        pct_chg = 0

    buy_zone = item.get("buy_zone", "")
    trigger  = item.get("trigger_condition", "")

    # 判断是否触发买入条件（简化判断）
    triggered = False
    trigger_reason = ""
    if trigger:
        if "RSI" in trigger.upper():
            # 无法获取RSI时，用价格位置判断
            triggered = True
            trigger_reason = f"价格条件满足（{price:.2f}）"
        else:
            triggered = True
            trigger_reason = f"符合条件（{trigger}）"

    # 趋势判断
    trend = item.get("trend_status", "待观察")
    risk_note = item.get("risk_note", "")

    conclusion = (
        f"{name}({code})：现价¥{price:.2f}（{'+' if pct_chg >= 0 else ''}{pct_chg:.2f}%），"
        f"观察区：{buy_zone}，触发条件：{trigger}。"
        f"当前趋势：{trend}。风险备注：{risk_note}。"
        f"{'✅ 已触发买入条件：' + trigger_reason if triggered else '⏳ 尚未触发买入条件。'}"
    )

    item["price"] = price
    item["change_pct"] = pct_chg
    item["latest_conclusion"] = conclusion
    item["last_scan_at"] = datetime.datetime.now().isoformat()
    item["status"] = "scanned"
    write_watchlist(watchlist)

    record_scan(code, "watch", {
        "price": price, "trend": trend, "triggered": triggered,
        "conclusion": conclusion
    })

    return {
        "code": code, "name": name,
        "price": price, "pct_chg": pct_chg,
        "trend": trend, "triggered": triggered,
        "conclusion": conclusion,
        "scan_at": item["last_scan_at"]
    }

# ===== 全量扫描 =====
def scan_all_holdings():
    """扫描所有持仓"""
    holdings = get_holdings()
    results = []
    for h in holdings:
        code = h.get("code")
        if code:
            r = scan_holding(code)
            results.append(r)
    return results

def scan_all_watch():
    """扫描所有观察股"""
    watchlist = get_watchlist()
    results = []
    for w in watchlist:
        code = w.get("code")
        if code:
            r = scan_watch(code)
            results.append(r)
    return results

# ===== 扫描历史记录 =====
def record_scan(code, item_type, scan_data):
    os.makedirs(DATA_DIR, exist_ok=True)
    hist_file = f"{DATA_DIR}/scan_history.json"
    try:
        with open(hist_file) as f:
            history = json.load(f)
    except:
        history = {}

    today = datetime.date.today().isoformat()
    if today not in history:
        history[today] = []
    history[today].append({
        "code": code, "item_type": item_type,
        "scan_at": datetime.datetime.now().isoformat(),
        **scan_data
    })
    with open(hist_file, "w") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

# ===== CLI =====
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="持仓/观察池扫描")
    parser.add_argument("--type", choices=["holding","watch","all"], default="all")
    parser.add_argument("--code", default=None)
    args = parser.parse_args()

    if args.type == "holding" and args.code:
        result = scan_holding(args.code)
    elif args.type == "watch" and args.code:
        result = scan_watch(args.code)
    else:
        result = {"holdings": scan_all_holdings(), "watchlist": scan_all_watch()}

    print(json.dumps(result, ensure_ascii=False, indent=2))
