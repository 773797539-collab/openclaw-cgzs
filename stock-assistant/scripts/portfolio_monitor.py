#!/usr/bin/env python3
"""
portfolio_monitor.py - 持仓监控主脚本
- 读取 watchlist.yaml 中的持仓
- 通过 MCP 实时查询每只股票现价
- 计算浮盈浮亏，更新 portfolio.json
- 技术信号告警（KDJ/RSI 超卖时飞书通知）
"""
import urllib.request, json, os, re
from datetime import datetime

WORKSPACE = "/home/admin/openclaw/workspace"
PORTFOLIO_JSON = f"{WORKSPACE}/portal/status/portfolio.json"
WATCHLIST = f"{WORKSPACE}/stock-assistant/data/watchlist.yaml"
MCP_URL = "http://82.156.17.205/cnstock/mcp"
FEISHU_TARGET = "ou_7e5fc2ebd19e226b5671475bd6d1bbdc"

def normalize_symbol(code):
    code = str(code).strip()
    if code.startswith("SH") or code.startswith("SZ"):
        return code.upper()
    elif code.startswith("6"):
        return "SH" + code
    elif code.startswith("0") or code.startswith("3"):
        return "SZ" + code
    return None

def call_mcp(symbol, depth="brief"):
    """MCP 查询（urllib 直连，兼容 SSE）"""
    normalized = normalize_symbol(symbol)
    if not normalized: return None
    payload = {"jsonrpc":"2.0","method":"tools/call",
               "params":{"name":depth,"arguments":{"symbol":normalized}},"id":1}
    try:
        req = urllib.request.Request(MCP_URL, data=json.dumps(payload).encode(),
            headers={"Content-Type":"application/json","Accept":"application/json, text/event-stream"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = resp.read().decode()
        idx = raw.find("data:")
        if idx < 0: return None
        result = json.loads(raw[idx+5:].strip()).get("result",{})
        return result if result else None
    except: return None

def get_full_tech(code):
    """获取完整技术指标（MCP full）"""
    normalized = normalize_symbol(code)
    if not normalized: return None
    payload = {"jsonrpc":"2.0","method":"tools/call",
               "params":{"name":"full","arguments":{"symbol":normalized}},"id":1}
    try:
        req = urllib.request.Request(MCP_URL, data=json.dumps(payload).encode(),
            headers={"Content-Type":"application/json","Accept":"application/json, text/event-stream"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = resp.read().decode()
        idx = raw.find("data:")
        if idx < 0: return None
        result = json.loads(raw[idx+5:].strip()).get("result",{})
        text = result.get("content",[{}])[0].get("text","") if result.get("content") else ""
        if not text: return None
        for line in text.split("\n"):
            if "| " not in line or "2026-" not in line: continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 20 or parts[1].count("-") != 2: continue
            try:
                return {
                    "kdj_k": float(parts[7]),
                    "kdj_d": float(parts[8]),
                    "macd_dif": float(parts[10]),
                    "macd_dea": float(parts[11]),
                    "rsi6": float(parts[12]),
                    "rsi12": float(parts[13]),
                }
            except: continue
        return None
    except: return None

def send_tech_alert(code, signal, detail):
    """发送技术信号告警到飞书"""
    try:
        import subprocess
        msg = f"\U0001F4C8 技术信号告警 | {code}\n\n\U0001F50D {signal}\n\n{detail}"
        subprocess.run([
            "openclaw", "message", "send",
            "--channel", "feishu",
            "--target", FEISHU_TARGET,
            "--message", msg
        ], capture_output=True, timeout=10)
        print(f"  \U0001F4E2 技术告警已发: {signal}")
    except Exception as e:
        print(f"  \U0001F4E2 告警发送失败: {e}")

def parse_brief_stock(text):
    """解析 MCP brief 返回的文本，提取关键字段"""
    info = {"name": "", "price": None, "change_pct": None, "pe_ratio": None, "pb_ratio": None}
    in_price = in_change = False
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("## 价格"): in_price, in_change = True, False
        elif line.startswith("## 涨跌幅"): in_change, in_price = True, False
        elif line.startswith("##") and "价格" not in line: in_price = in_change = False
        if "股票名称:" in line: info["name"] = line.split(":", 1)[1].strip()
        if "市盈率(静):" in line:
            m = re.search(r'市盈率\(静\):\s*([\d.]+)', line)
            if m: info["pe_ratio"] = float(m.group(1))
        if "市净率:" in line:
            m = re.search(r'市净率:\s*([\d.]+)', line)
            if m: info["pb_ratio"] = float(m.group(1))
        if in_price and "当日:" in line and "%" not in line:
            m = re.search(r'当日:\s*([\d.]+)', line)
            if m and info["price"] is None: info["price"] = float(m.group(1))
        if in_change and "当日:" in line and "%" in line:
            m = re.search(r'当日:\s*([+-]?[\d.]+)%', line)
            if m: info["change_pct"] = float(m.group(1))
    return info

def read_watchlist():
    holdings = []
    if not os.path.exists(WATCHLIST): return holdings
    with open(WATCHLIST) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"): continue
            parts = line.split("#")[0].strip().split()
            if len(parts) < 3: continue
            holdings.append({"code": parts[0], "shares": int(parts[1]), "cost": float(parts[2])})
    return holdings

def update_portfolio():
    """主更新流程（含技术信号告警）"""
    holdings = read_watchlist()
    if not holdings: print("无持仓数据"); return
    updated = []
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")

    for h in holdings:
        code = h["code"]
        result = call_mcp(code)
        if not result:
            print(f"  {code}: MCP查询失败，跳过"); continue
        text = result.get("content",[{}])[0].get("text","") if result.get("content") else ""
        if not text: continue
        info = parse_brief_stock(text)
        price = info["price"]; change_pct = info["change_pct"]
        name = info["name"] or code; shares = h["shares"]; cost = h["cost"]
        mv = price * shares; profit = mv - cost * shares; profit_pct = (price - cost) / cost * 100

        print(f"  {name}({code}): ¥{price} ({change_pct:+.2f}%) | 成本¥{cost} 浮亏{profit_pct:+.1f}%")

        # 技术信号告警检查（浮亏超10%时触发）
        tech = get_full_tech(code)
        if tech and profit_pct < -10:
            kdj = tech["kdj_k"]; rsi6 = tech["rsi6"]
            macd_state = "红区" if tech["macd_dif"] > tech["macd_dea"] else "绿区"
            if kdj < 20:
                send_tech_alert(code, f"KDJ超卖+深度套牢({profit_pct:.1f}%)",
                    f"KDJ K={kdj:.1f}(超卖)\nRSI6={rsi6:.1f}\nMACD:{macd_state}\n成本¥{cost} 现价¥{price}\n浮亏{profit_pct:.1f}%")
            elif rsi6 < 30:
                send_tech_alert(code, f"RSI6超卖({rsi6:.0f})",
                    f"RSI6={rsi6:.1f}提示超卖\nKDJ K={kdj:.1f}\nMACD:{macd_state}")

        updated.append({
            "code": code, "name": name, "shares": shares, "cost": cost,
            "price": price, "change_pct": change_pct,
            "market_value": round(mv, 2), "profit": round(profit, 2),
            "profit_pct": round(profit_pct, 2),
            "pe_ratio": info["pe_ratio"], "pb_ratio": info["pb_ratio"],
            "updated_at": now
        })

    total_mv = sum(h["market_value"] for h in updated)
    total_cost = sum(h["cost"] * h["shares"] for h in updated)
    total_profit = total_mv - total_cost
    total_profit_pct = (total_mv - total_cost) / total_cost * 100 if total_cost else 0
    portfolio = {"updated_at": now, "total_value": round(total_mv, 2),
                  "total_cost": round(total_cost, 2), "total_profit": round(total_profit, 2),
                  "profit_pct": round(total_profit_pct, 2), "currency": "CNY",
                  "holdings": updated}
    with open(PORTFOLIO_JSON, "w") as f:
        json.dump(portfolio, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 持仓已更新: 总市值¥{total_mv:.2f} 浮亏¥{total_profit:.2f}({total_profit_pct:.2f}%)")

if __name__ == "__main__":
    update_portfolio()
