#!/usr/bin/env python3
"""
mcp_stock.py - MCP A股查询封装
通过 MCP HTTP 接口获取实时行情，替代不稳定的 akshare 直连
"""
import sys
import json
import re
import urllib.request
from typing import Optional, Dict, Any

MCP_URL = "http://82.156.17.205/cnstock/mcp"

def normalize_symbol(symbol: str) -> Optional[str]:
    """统一股条格式：6开头->SH，0/3开头->SZ"""
    symbol = str(symbol).strip()
    if symbol.startswith("SH") or symbol.startswith("SZ"):
        return symbol.upper()
    elif symbol.startswith("6"):
        return "SH" + symbol
    elif symbol.startswith("0") or symbol.startswith("3"):
        return "SZ" + symbol
    return None

def call_mcp(tool_name: str, args: Dict[str, Any], retry: int = 3) -> Optional[Dict]:
    """调用 MCP 工具（urllib 直连，兼容 SSE，支持重试）"""
    import time
    last_err = None
    for attempt in range(retry):
        try:
            payload = {"jsonrpc": "2.0", "method": "tools/call",
                       "params": {"name": tool_name, "arguments": args}, "id": 1}
            req = urllib.request.Request(MCP_URL, data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json",
                         "Accept": "application/json, text/event-stream"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                raw = resp.read().decode()
            idx = raw.find("data:")
            if idx < 0: return None
            result = json.loads(raw[idx+5:].strip()).get("result", {})
            return result if result else None
        except Exception as e:
            last_err = e
            if attempt < retry - 1:
                time.sleep(0.5 * (attempt + 1))  # 递增等待
    return None

def get_stock_info(symbol: str) -> Optional[Dict[str, Any]]:
    """获取个股实时行情（价格+涨跌幅+PE+PB）"""
    normalized = normalize_symbol(symbol)
    if not normalized:
        return None
    result = call_mcp("brief", {"symbol": normalized})
    if not result:
        return None
    text = ""
    if isinstance(result.get("content"), list):
        for item in result["content"]:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text", "")
                break
    if not text:
        return None
    info = {"symbol": symbol, "name": "", "price": None, "change_pct": None, "pe_ratio": None, "pb_ratio": None}
    in_price_section = False
    in_change_section = False
    for line in text.split("\n"):
        line = line.strip()
        # 识别当前在哪个区块
        if line == "## 价格" or line.startswith("## 价格"):
            in_price_section = True
            in_change_section = False
        elif line == "## 涨跌幅" or line.startswith("## 涨跌幅"):
            in_change_section = True
            in_price_section = False
        elif line.startswith("##"):
            in_price_section = False
            in_change_section = False
        # 股票信息
        if "股票代码:" in line:
            info["symbol"] = line.split(":", 1)[1].strip()
        if "股票名称:" in line:
            info["name"] = line.split(":", 1)[1].strip()
        # 财务指标
        if "市盈率(静):" in line:
            m = re.search(r'市盈率\(静\):\s*([\d.]+)', line)
            if m:
                info["pe_ratio"] = float(m.group(1))
        if "市净率:" in line:
            m = re.search(r'市净率:\s*([\d.]+)', line)
            if m:
                info["pb_ratio"] = float(m.group(1))
        # 价格（在价格区块）
        if in_price_section and "当日:" in line and "%" not in line:
            m = re.search(r'当日:\s*([\d.]+)', line)
            if m and info["price"] is None:
                info["price"] = float(m.group(1))
        # 涨跌幅（在涨跌幅区块）
        if in_change_section and "当日:" in line and "%" in line:
            m = re.search(r'当日:\s*([+-]?[\d.]+)%', line)
            if m:
                info["change_pct"] = float(m.group(1))
    return info

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: mcp_stock.py <股票代码>")
        sys.exit(1)
    info = get_stock_info(sys.argv[1])
    if info:
        print(json.dumps(info, ensure_ascii=False, indent=2))
    else:
        print(json.dumps({"error": "查询失败", "symbol": sys.argv[1]}))
        sys.exit(1)

def get_medium_info(symbol: str) -> Optional[Dict[str, Any]]:
    """获取个股完整中频数据（medium），包含资金流向、换手率、5年财务数据"""
    normalized = normalize_symbol(symbol)
    if not normalized:
        return None
    result = call_mcp("medium", {"symbol": normalized})
    if not result:
        return None
    text = ""
    if isinstance(result.get("content"), list):
        for item in result["content"]:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text", "")
                break
    if not text:
        return None

    info = {
        "symbol": normalized,
        "name": "",
        "price": None,
        "change_pct": None,
        "pe_ratio": None,
        "pb_ratio": None,
        "roe": None,
        "main_net_inflow": None,    # 主力净流入（亿元）
        "turnover": None,            # 当日换手率%
        "market_cap": None,           # 流通市值（亿元）
        "high_5d": None, "low_5d": None,
        "high_20d": None, "low_20d": None,
        "pct_5d": None, "pct_20d": None,
        "vol_5d_avg": None,           # 5日均量（万手）
    }

    section = ""
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("## "):
            section = line
            continue
        if "股票代码:" in line:
            info["symbol"] = line.split(":", 1)[1].strip()
        if "股票名称:" in line:
            info["name"] = line.split(":", 1)[1].strip()
        # 基本面
        if "市盈率(静):" in line:
            m = re.search(r'市盈率\(静\):\s*([\d.]+)', line)
            if m: info["pe_ratio"] = float(m.group(1))
        if "市净率:" in line:
            m = re.search(r'市净率:\s*([\d.]+)', line)
            if m: info["pb_ratio"] = float(m.group(1))
        if "净资产收益率" in line and "2024" not in line:
            m = re.search(r'净资产收益率:\s*([\d.]+)', line)
            if m: info["roe"] = float(m.group(1))
        # 价格
        if section == "## 价格" and "当日:" in line and "%" not in line:
            m = re.search(r'当日:\s*([\d.]+)', line)
            if m: info["price"] = float(m.group(1))
        if section == "## 价格" and "5日均价:" in line:
            m = re.search(r'5日均价:\s*([\d.]+)', line)
            if m: info["price_5d_avg"] = float(m.group(1))
        # 涨跌幅
        if section == "## 涨跌幅" and "当日:" in line and "%" in line:
            m = re.search(r'当日:\s*([+-]?[\d.]+)%', line)
            if m: info["change_pct"] = float(m.group(1))
        if section == "## 涨跌幅" and "5日累计:" in line:
            m = re.search(r'5日累计:\s*([+-]?[\d.]+)%', line)
            if m: info["pct_5d"] = float(m.group(1))
        if section == "## 涨跌幅" and "20日累计:" in line:
            m = re.search(r'20日累计:\s*([+-]?[\d.]+)%', line)
            if m: info["pct_20d"] = float(m.group(1))
        # 成交量
        if section == "## 成交量(万手)" and "5日均量(万手):" in line:
            m = re.search(r'5日均量\(万手\):\s*([\d.]+)', line)
            if m: info["vol_5d_avg"] = float(m.group(1))
        # 资金流向
        if section == "## 资金流向":
            if "主力" in line and "流入:" in line:
                m = re.search(r'主力.*?流入:\s*([\d.]+)亿', line)
                if m: info["main_net_inflow"] = float(m.group(1))  # 单位：亿
        # 换手率
        if section == "## 换手率" and "当日:" in line and "%" in line:
            m = re.search(r'当日:\s*([\d.]+)%', line)
            if m: info["turnover"] = float(m.group(1))
        # 流通市值
        if "流通市值:" in line:
            m = re.search(r'流通市值:\s*([\d.]+)(亿|万)', line)
            if m:
                val = float(m.group(1))
                if m.group(2) == "万": val /= 10000
                info["market_cap"] = val
    return info


def parse_full_technical(text: str) -> Optional[Dict[str, Any]]:
    """解析 MCP full 返回的 30 天技术指标历史数据表

    返回结构: {
        "latest": {...},  # 最新一天数据
        "history": [...]  # 最近30天历史列表（按日期倒序）
    }

    单日字段: date, ma5, ma10, ma30, ma60, ma120,
             kdj_k, kdj_d, kdj_j, macd_dif, macd_dea,
             rsi6, rsi12, rsi24, boll_upper, boll_middle, boll_lower, obv, atr
    """
    history = []
    for line in text.split(chr(10)):
        if "| " not in line or line.strip().startswith("| ---"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 19 or not parts[1]:
            continue
        date = parts[1]
        if date.count("-") != 2:
            continue
        try:
            row = {
                "date": date,
                "ma5": float(parts[2]),
                "ma10": float(parts[3]),
                "ma30": float(parts[4]),
                "ma60": float(parts[5]),
                "ma120": float(parts[6]),
                "kdj_k": float(parts[7]),
                "kdj_d": float(parts[8]),
                "kdj_j": float(parts[9]),
                "macd_dif": float(parts[10]),
                "macd_dea": float(parts[11]),
                "rsi6": float(parts[12]),
                "rsi12": float(parts[13]),
                "rsi24": float(parts[14]),
                "boll_upper": float(parts[15]),
                "boll_middle": float(parts[16]),
                "boll_lower": float(parts[17]),
                "obv": float(parts[18]) if parts[18] else None,
                "atr": float(parts[19]) if len(parts) > 19 and parts[19] else None,
            }
            history.append(row)
        except (ValueError, IndexError):
            continue
    return {"latest": history[0] if history else None, "history": history} if history else None
