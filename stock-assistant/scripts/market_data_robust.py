#!/usr/bin/env python3
"""
market_data_robust.py - 多源市场数据获取器
策略：MCP(主) → akshare(备) → 缓存(最后手段)
"""
import time, json, urllib.request, subprocess
from pathlib import Path

CACHE_FILE = Path("/home/admin/openclaw/workspace/data/last_price_cache.json")
MCP_SERVERS = [
    "http://82.156.17.205:8000",
]
AKSHARE_TIMEOUT = 8
MCP_TIMEOUT = 5
TENCENT_TIMEOUT = 5


def get_from_cache(code):
    """从本地缓存读取最近价格"""
    if not CACHE_FILE.exists():
        return None
    try:
        with open(CACHE_FILE) as f:
            cache = json.load(f)
        entry = cache.get(code)
        if not entry:
            return None
        age = time.time() - entry.get("ts", 0)
        if age < 300:  # 5分钟内
            return entry.get("price")
    except Exception:
        pass
    return None


def get_realtime_mcp(code):
    """从 MCP 服务器获取实时价格（主路径）"""
    for server in MCP_SERVERS:
        url = f"{server}/stock/realtime?codes={code}"
        try:
            req = urllib.request.urlopen(url, timeout=MCP_TIMEOUT)
            data = json.loads(req.read())
            for item in data.get("data", []):
                price = item.get("price")
                if price:
                    _update_cache(code, price)
                    return price
        except Exception:
            continue
    return None


def get_realtime_akshare(code):
    """akshare 备用获取"""
    try:
        import akshare as ak
        df = ak.stock_zh_a_spot_em()
        row = df[df["代码"] == code]
        if not row.empty:
            price = float(row.iloc[0]["最新价"])
            _update_cache(code, price)
            return price
    except Exception as e:
        print(f"akshare error: {e}")
    return None


def get_realtime_tencent(code):
    """腾讯财经 API（免费，稳定）"""
    # code: sh605365 格式
    if not code.startswith(("sh", "sz")):
        code = "sh" + code
    url = f"https://qt.gtimg.cn/q={code}"
    try:
        req = urllib.request.urlopen(url, timeout=TENCENT_TIMEOUT)
        data = req.read().decode("gbk")
        # 格式: v_sh605365="1~立达信~605365~18.16~18.35~..."
        m = data.split("~")
        if len(m) > 4:
            price = float(m[3])
            _update_cache(code, price)
            return price
    except Exception as e:
        print(f"Tencent API error: {e}")
    return None


def _update_cache(code, price):
    """更新本地缓存"""
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    cache = {}
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE) as f:
                cache = json.load(f)
        except Exception:
            pass
    cache[code] = {"price": price, "ts": time.time()}
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, ensure_ascii=False)


def get_price(code):
    """
    获取股票实时价格
    优先级：MCP(主) → akshare(备) → 缓存(最后手段)
    返回：(price, source, age_seconds)
    """
    # 1. MCP 主路径
    price = get_realtime_mcp(code)
    if price:
        return price, "mcp", 0

    # 2. 腾讯财经（免费，稳定）
    price = get_realtime_tencent(code)
    if price:
        return price, "tencent", 0

    # 3. akshare 备用
    price = get_realtime_akshare(code)
    if price:
        return price, "akshare", 0

    # 3. 缓存最后手段
    price = get_from_cache(code)
    if price:
        return price, "cache", int(time.time() - CACHE_FILE.stat().st_mtime)
    return None, "none", -1


if __name__ == "__main__":
    import sys
    code = sys.argv[1] if len(sys.argv) > 1 else "605365"
    price, source, age = get_price(code)
    print(f"{code}: {price} (来源:{source}, 缓存年龄:{age}s)")
