#!/usr/bin/env python3
"""
stock_scan.py - 个股技术面批量扫描工具
用法: python3 stock_scan.py [codes...]
不传参时扫描默认候选股
"""
import sys, os, datetime

# 确保 mcp_utils 可导入
sys.path.insert(0, os.path.dirname(__file__))
from mcp_utils import mcp_full as _mcp_full, mcp_brief as _mcp_brief, normalize_symbol

MCP_URL = "http://82.156.17.205/cnstock/mcp"

# ============ 交易时段判断 ============
def is_trading_day():
    today = datetime.datetime.now()
    if today.weekday() >= 5:
        return False
    return True

def is_trading_time():
    now = datetime.datetime.now()
    t = now.time()
    morning_start = datetime.time(9, 30)
    morning_end   = datetime.time(11, 30)
    afternoon_start = datetime.time(13, 0)
    afternoon_end   = datetime.time(15, 0)
    return (morning_start <= t <= morning_end) or (afternoon_start <= t <= afternoon_end)

def can_scan():
    if not is_trading_day():
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 今日非交易日（周末/节假日），跳过扫描")
        return False
    if not is_trading_time():
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 当前非交易时段，跳过扫描")
        return False
    return True
# =====================================

def mcp_brief_name(symbol):
    """Get stock name (normalizes symbol first)"""
    text = _mcp_brief(normalize_symbol(symbol))
    if not text:
        return ""
    first_line = text.split("\n")[0].strip()
    import re
    return re.sub(r'\(\d+\)', '', first_line).strip()

def mcp_full_text(symbol):
    """MCP full query (normalizes symbol first)"""
    return _mcp_full(normalize_symbol(symbol)) or ""

def parse_tech(text):
    """解析技术指标表格"""
    rows = []
    for line in text.split("\n"):
        if "| " not in line or line.strip().startswith("| ---"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 20 or not parts[1] or parts[1].count("-") != 2:
            continue
        try:
            rows.append({
                "date": parts[1],
                "ma5": float(parts[2]), "ma10": float(parts[3]), "ma30": float(parts[4]),
                "ma60": float(parts[5]), "ma120": float(parts[6]),
                "kdj_k": float(parts[7]), "kdj_d": float(parts[8]), "kdj_j": float(parts[9]),
                "macd_dif": float(parts[10]), "macd_dea": float(parts[11]),
                "rsi6": float(parts[12]), "rsi12": float(parts[13]), "rsi24": float(parts[14]),
                "boll_upper": float(parts[15]), "boll_middle": float(parts[16]), "boll_lower": float(parts[17]),
            })
        except:
            continue
    return rows

def scan_code(code):
    sym = normalize_symbol(code)
    text = mcp_full_text(sym)
    if not text:
        return None
    in_tech = False
    tech_lines = []
    for line in text.split("\n"):
        if "技术指标" in line:
            in_tech = True
        if in_tech:
            tech_lines.append(line)
    hist = parse_tech("\n".join(tech_lines))
    if len(hist) < 2:
        return None
    latest = hist[0]
    prev = hist[1] if len(hist) > 1 else None
    dif, dea = latest["macd_dif"], latest["macd_dea"]
    dif_p, dea_p = (prev["macd_dif"], prev["macd_dea"]) if prev else (None, None)
    if dif_p is not None and dif > dea and dif_p <= dea_p:
        macd_signal = "✨金叉"
    elif dif_p is not None and dif < dea and dif_p >= dea_p:
        macd_signal = "💀死叉"
    elif dif > dea:
        macd_signal = "▲红区"
    else:
        macd_signal = "▼绿区"
    k = latest["kdj_k"]
    kdj_s = "⚠️超卖" if k < 20 else "⚠️超买" if k > 80 else "正常"
    r = latest["rsi6"]
    rsi_s = "⚠️超卖" if r < 30 else "⚠️超买" if r > 70 else "正常"
    ma_trend = "▲上升" if latest["ma5"] > latest["ma30"] else "▼下降"
    name = mcp_brief_name(sym)
    return {
        "code": code, "name": name,
        "dif": dif, "dea": dea, "macd_signal": macd_signal,
        "kdj_k": k, "kdj_state": kdj_s,
        "rsi6": r, "rsi_state": rsi_s,
        "ma_trend": ma_trend,
        "ma5": latest["ma5"], "ma30": latest["ma30"], "ma60": latest["ma60"],
    }

def main():
    if not can_scan():
        return None
    codes = sys.argv[1:] if len(sys.argv) > 1 else ["SH605365","SH600036","SH601318","SZ000001","SH300750"]
    results = []
    for code in codes:
        r = scan_code(code)
        if r:
            results.append(r)
    if not results:
        print("无结果")
        return None
    print(f"MACD金叉候选股扫描（{len(results)}只）：")
    print(f"{'代码':<12} {'名称':<10} {'DIF':>8} {'DEA':>8} {'MACD':>8} {'KDJ_K':>7} {'RSI6':>6} {'MA趋势':>6}")
    print("-" * 70)
    for r in results:
        print(f"{r['code']:<12} {r['name']:<10} {r['dif']:>8.3f} {r['dea']:>8.3f} {r['macd_signal']:>8} {r['kdj_k']:>7.1f} {r['rsi6']:>6.1f} {r['ma_trend']:>6}")
    print(f"\n扫描完成 {len(results)} 只")
    return {"results": results, "count": len(results), "scan_time": str(datetime.datetime.now())}

if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    if "--dry-run" in args or "-n" in args:
        from datetime import datetime
        print("=== stock_scan dry-run 模式 ===")
        print(f"当前: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"交易日: {datetime.datetime.now().weekday() < 5}")
        print(f"可运行: {can_scan()}")
        sys.exit(0)
    if "--json" in args:
        import json
        result = main()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        main()
