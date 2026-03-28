# mcp_utils.py - MCP unified caller (urllib direct, SSE compatible)
# All scripts import from here. Avoids duplicate code.
# API: mcp_brief, mcp_medium, mcp_full, mcp_full_safe, normalize_symbol, mcp_health_check
# MCP: http://82.156.17.205/cnstock/mcp
# Note: MCP full on some stocks (e.g. SH605365) returns empty - use mcp_full_safe
import urllib.request, json, re
from typing import Optional, Dict, Any

MCP_URL = "http://82.156.17.205/cnstock/mcp"

def mcp_call(tool: str, args: Dict[str, Any], timeout: int = 8) -> Optional[Dict]:
    """调用 MCP 工具（urllib 直连，兼容 SSE）"""
    payload = {"jsonrpc":"2.0","method":"tools/call",
               "params":{"name":tool,"arguments":args},"id":1}
    try:
        req = urllib.request.Request(
            MCP_URL, data=json.dumps(payload).encode(),
            headers={"Content-Type":"application/json",
                     "Accept":"application/json, text/event-stream"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
        idx = raw.find("data:")
        if idx < 0: return None
        result = json.loads(raw[idx+5:].strip()).get("result", {})
        return result if result else None
    except: return None

def mcp_brief(symbol: str) -> Optional[str]:
    """MCP brief 查询，返回文本（价格/PE/PB/名称）"""
    result = mcp_call("brief", {"symbol": symbol})
    if not result: return None
    return result.get("content",[{}])[0].get("text","") if result.get("content") else None

def mcp_medium(symbol: str) -> Optional[str]:
    """MCP medium 查询，返回文本（+资金流向/换手率/振幅/行业概念）"""
    result = mcp_call("medium", {"symbol": symbol})
    if not result: return None
    return result.get("content",[{}])[0].get("text","") if result.get("content") else None

def mcp_full(symbol: str, timeout: int = 8) -> Optional[str]:
    """MCP full 查询，返回文本（完整技术指标：MA/KDJ/MACD/RSI/BOLL/ATR/OBV）"""
    result = mcp_call("full", {"symbol": symbol}, timeout=timeout)
    if not result: return None
    return result.get("content",[{}])[0].get("text","") if result.get("content") else None

def mcp_full_safe(symbol: str, timeout: int = 8) -> Optional[str]:
    """MCP full 查询，带容错：部分股票MCP不支持full时降级到medium"""
    text = mcp_full(symbol, timeout=timeout)
    if text and "No data found" not in text:
        return text
    text2 = mcp_medium(symbol)
    if text2:
        return f"[full降级为medium]\n{text2}"
    return None

def normalize_symbol(code: str) -> str:
    """标准化股票代码为 SH/SZ 前缀格式
    605365 → SH605365, 000001 → SZ000001
    """
    code = str(code).strip()
    if code.startswith(("SH","SZ")): return code.upper()
    return ("SH" if code.startswith(("6","5")) else "SZ") + code

def parse_tech_table(text: str) -> list:
    """解析 MCP full 返回的技术指标表格，返回历史数据列表
    解析字段: date, ma5/10/30/60/120, kdj_k/d/j, macd_dif/dea, rsi6/12/24, boll_upper/middle/lower
    """
    rows = []
    for line in text.split("\n"):
        if "| " not in line or line.strip().startswith("| ---"): continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 20 or not parts[1] or parts[1].count("-") != 2: continue
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
        except: continue
    return rows

def mcp_health_check(timeout=5):
    """MCP 服务器健康检查，返回 (ok, latency_ms, error)"""
    import time
    start = time.time()
    try:
        result = mcp_call("brief", {"symbol": "SH605365"}, timeout=timeout)
        latency = (time.time() - start) * 1000
        if result is not None:
            return True, latency, None
        return False, latency, "result is None"
    except Exception as e:
        latency = (time.time() - start) * 1000
        return False, latency, str(e)

if __name__ == "__main__":
    ok, latency, err = mcp_health_check()
    print(f"MCP健康检查: {'OK' if ok else 'FAIL'} ({latency:.0f}ms)" + (f" | {err}" if err else ""))
