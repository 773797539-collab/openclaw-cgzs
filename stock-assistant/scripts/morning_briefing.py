#!/usr/bin/env python3
"""morning_briefing.py - 每日 A 股开盘前简报生成"""
import os, json, re, urllib.request, sys
from datetime import datetime

# MCP 统一调用复用
sys.path.insert(0, os.path.dirname(__file__))
from mcp_utils import mcp_brief as _mcp_brief, MCP_URL

WORKSPACE = "/home/admin/openclaw/workspace"
WATCHLIST = f"{WORKSPACE}/stock-assistant/data/watchlist.yaml"
PORTFOLIO_CACHE = f"{WORKSPACE}/portal/status/portfolio.json"
REPORT_DIR = f"{WORKSPACE}/stock-assistant/reports"

def mcp_brief(symbol):
    """Wrap mcp_utils mcp_brief with normalization"""
    from mcp_utils import normalize_symbol
    return _mcp_brief(normalize_symbol(symbol))

def get_gap_status():
    try:
        if os.path.exists(PORTFOLIO_CACHE):
            with open(PORTFOLIO_CACHE) as f: portfolio = json.load(f)
        else: return "跳空数据不可用"
        holdings = portfolio.get("holdings", []) or []
        if not holdings: return "无持仓"
        total = sum(h.get("market_value",0) for h in holdings)
        cost = sum(h.get("shares",0)*h.get("cost",0) for h in holdings)
        pct = (total-cost)/cost*100 if cost > 0 else 0
        return f"持仓：总市值¥{total:.0f} {pct:+.1f}%"
    except: return "跳空数据读取异常"

def get_market_sectors():
    # industry_hot 尝试（session 级，不可用时降级）
    try:
        payload = {"jsonrpc":"2.0","method":"tools/call",
                   "params":{"name":"industry_hot","arguments":{}},"id":1}
        req = urllib.request.Request(MCP_URL, data=json.dumps(payload).encode(),
            headers={"Content-Type":"application/json","Accept":"application/json, text/event-stream"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            raw = resp.read().decode()
        idx = raw.find("data:")
        if idx >= 0:
            result = json.loads(raw[idx+5:].strip()).get("result",{})
            text = result.get("content",[{}])[0].get("text","") if result.get("content") else ""
            if text and "Unknown tool" not in text and len(text) > 50:
                lines = text.split("\n"); sector_lines, in_sector = [], False
                for line in lines:
                    if "## 市场主线" in line: in_sector = True; continue
                    if in_sector and line.startswith("##"): break
                    if in_sector and line.strip(): sector_lines.append(line.strip())
                if sector_lines: return sector_lines[:6]
    except: pass
    return ["板块数据: 暂不可用"]

def get_us_etf():
    results = []
    for code, name in [("SH513500","标普500ETF"), ("SH513100","纳斯达克ETF")]:
        text = mcp_brief(code)
        if text:
            for line in text.split("\n"):
                line = line.strip()
                if "当日:" in line and "%" in line:
                    m = re.search(r'当日:\s*([+-]?[\d.]+)%', line)
                    if m:
                        pct = float(m.group(1))
                        results.append(f"{name}: {'+' if pct>=0 else ''}{pct:.2f}%"); break
            else: results.append(f"{name}: 解析失败")
        else: results.append(f"{name}: 无数据")
    return results

def get_tech_summary():
    """持仓股技术面摘要（MCP full，fast，8秒超时）"""
    try:
        payload = {"jsonrpc":"2.0","method":"tools/call",
                   "params":{"name":"full","arguments":{"symbol":"SH605365"}},"id":1}
        req = urllib.request.Request(MCP_URL, data=json.dumps(payload).encode(),
            headers={"Content-Type":"application/json","Accept":"application/json, text/event-stream"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = resp.read().decode()
        idx = raw.find("data:")
        if idx < 0: return None
        result = json.loads(raw[idx+5:].strip()).get("result",{})
        text = result.get("content",[{}])[0].get("text","") if result.get("content") else ""
        if not text: return None
        # 解析第一行技术指标（最新日期行）
        for line in text.split("\n"):
            if "| " not in line or "2026-" not in line or line.strip().startswith("| ---"): continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 20 or parts[1].count("-") != 2: continue
            try:
                ma5,ma10,ma30 = float(parts[2]),float(parts[3]),float(parts[4])
                macd_d,macd_de = float(parts[10]),float(parts[11])
                k = float(parts[7])
                rsi6 = float(parts[12])
                boll_u,boll_m,boll_l = float(parts[15]),float(parts[16]),float(parts[17])
                price = 18.35  # 持仓现价
                trend = "▲" if ma5 > ma30 else "▼"
                macd_s = "▲" if macd_d > macd_de else "▼"
                kdj_s = "超卖" if k < 20 else "超买" if k > 80 else "正常"
                boll_pos = (price-boll_l)/(boll_u-boll_l)*100 if boll_u!=boll_l else 50
                return (f"MA5{ma5:.2f}{trend}MA30{ma30:.2f} | "
                        f"MACD{macd_s}{macd_d:.2f}/{macd_de:.2f} | "
                        f"KDJ K={k:.0f}({kdj_s}) | RSI6={rsi6:.0f} | 布林{boll_pos:.0f}%")
            except: pass
        return None
    except: return None

def generate_report():
    now = datetime.now().strftime("%Y-%m-%d 08:30 GMT+8")
    lines = [f"# 每日 A 股开盘前简报\n\n生成时间: {now} | 数据来源: MCP\n\n",
             "**【大盘情绪】**\n", get_gap_status(), "\n\n",
             "**【市场热点板块】**\n"]
    for s in get_market_sectors(): lines.append(s + "\n")
    lines.extend(["\n**【美股隔夜参考】**\n"])
    for etf in get_us_etf(): lines.append(f"- {etf}\n")
    lines.extend(["\n**【持仓技术信号】**\n"])
    tech = get_tech_summary()
    if tech: lines.append(f"- {tech}\n")
    else: lines.append("- 技术信号：暂不可用\n")
    lines.extend(["\n**【持仓状况】**\n"])
    if os.path.exists(WATCHLIST):
        try:
            with open(WATCHLIST) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"): continue
                    parts = line.split("#")[0].strip().split()
                    if len(parts) < 2: continue
                    code, shares = parts[0], parts[1]
                    cost = float(parts[2]) if len(parts) >= 3 else 0
                    prefix = "SH" if code.startswith(("6","5")) else "SZ"
                    text = mcp_brief(prefix + code)
                    if not text: lines.append(f"- {code}: MCP查询失败\n"); continue
                    name = code; price_val = pct_val = None
                    for ln in text.split("\n"):
                        ln = ln.strip()
                        if "股票名称:" in ln: name = ln.split(":",1)[1].strip()
                        if "当日:" in ln and "最高:" in ln and "%" not in ln:
                            try: price_val = float(ln.split(":",1)[1].strip().split()[0])
                            except: pass
                        if "当日:" in ln and "%" in ln:
                            m = re.search(r'当日:\s*([+-]?[\d.]+)%', ln)
                            if m: pct_val = float(m.group(1))
                    if price_val:
                        mv = price_val * int(shares)
                        profit = (price_val-cost)*int(shares) if cost else 0
                        pct = (price_val-cost)/cost*100 if cost else 0
                        sign = "+" if pct >= 0 else ""
                        lines.append(f"- **{name}({code})**: ¥{price_val} {sign}{pct_val:.2f}% | 市值¥{mv:.0f} {sign}¥{profit:.0f} ({sign}{pct:.1f}%)\n")
                    else: lines.append(f"- {name}({code}): 价格获取失败\n")
        except Exception as e: lines.append(f"- 持仓读取异常: {e}\n")
    else: lines.append("_无持仓数据_\n")
    lines.extend(["\n---\n", "*由 OpenClaw 自动生成 | 仅供参考，不构成投资建议*\n"])
    return "".join(lines)

def save_report():
    report = generate_report()
    today = datetime.now().strftime("%Y-%m-%d")
    os.makedirs(REPORT_DIR, exist_ok=True)
    report_file = f"{REPORT_DIR}/daily-{today}.md"
    with open(report_file, "w") as f: f.write(report)
    print(f"早报已保存: {report_file} ({len(report)} 字符)")
    return report

def can_run():
    """判断是否需要生成早报（非交易时段快速退出）"""
    now = datetime.now()
    weekday = now.weekday()
    if weekday >= 5:
        print(f"[{now.strftime('%H:%M:%S')}] 今日非交易日（周末），跳过早报生成")
        return False
    t = now.time()
    morning_start = time(9, 30)
    morning_end   = time(11, 30)
    afternoon_start = time(13, 0)
    afternoon_end   = time(15, 0)
    if not (morning_start <= t <= morning_end or afternoon_start <= t <= afternoon_end):
        # 交易时段外，可生成但不推送（可选），这里直接跳过节省token
        print(f"[{now.strftime('%H:%M:%S')}] 当前非交易时段，跳过早报生成")
        return False
    return True

if __name__ == "__main__":
    import sys
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    if dry_run:
        from datetime import datetime
        now = datetime.now()
        print("=== morning_briefing dry-run 模式 ===")
        print(f"当前: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"交易日: {now.weekday() < 5}")
        print(f"可运行: {can_run()}")
        print("（实际不生成报告，不推送飞书）")
        sys.exit(0)
    elif can_run():
        save_report()
    else:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 非交易时段或周末，退出")
