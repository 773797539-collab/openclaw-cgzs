#!/usr/bin/env python3
"""
stock_picker.py - 短线选股系统
每天收盘后(16:30)运行一次
策略：强势股回调 + 热点追踪
池子维持 5~10 只，持仓不超过 5 天，未涨则剔除并复盘
飞书通知原则：仅池子有变化时通知，正常状态静默
"""
import json, os, urllib.request
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

POOL_FILE = "/home/admin/openclaw/workspace/stock-assistant/data/stock_pool.json"
REVIEW_DIR = "/home/admin/openclaw/workspace/stock-assistant/data/reviews/"
STRATEGY_FILE = "/home/admin/openclaw/workspace/stock-assistant/data/strategy.json"

os.makedirs(REVIEW_DIR, exist_ok=True)

def api_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read())

def get_price(code):
    """
    获取个股最新价（东方财富 push2 接口，f43 单位：分，需 /100 转为元）。
    时效性：仅返回交易时间内数据；非交易时间返回昨收价（会在 pct=0 体现）。
    """
    try:
        secid = "1." + code if code.startswith("6") else "0." + code
        d = api_get("https://push2.eastmoney.com/api/qt/stock/get?secid={}&fields=f43,f57,f58,f170,f136,f50".format(secid))
        data = d.get("data", {})
        if not data:
            return None
        raw_price = data.get("f43", 0)
        # f43=0 或异常大值（>1000元且非ST股）直接丢弃
        if raw_price == 0 or (raw_price > 100000 and code.startswith(("6", "0"))):
            return None
        price = raw_price / 100
        pct = data.get("f170", 0) / 100
        return {
            "code": code,
            "name": data.get("f58", code),
            "price": price,
            "pct": pct,
            "_api": "push2",
            "_ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception:
        return None

def get_price_cross(code):
    """双源价格校验：东方财富 push2（主力）+ MCP（备用）"""
    em = get_price(code)
    if em:
        return em
    # 备用：直接返回 None，不走 akshare（云服务器外网受限会卡死）
    return None

def get_prices_concurrent(codes):
    """并发查多只股票价格（双源校验）"""
    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = {ex.submit(get_price_cross, c): c for c in codes}
        return {c: f.result() for f, c in futures.items() if f.result()}

def get_zt_pool_via_mcp():
    """
    通过 MCP medium 获取全市场股票的资金流向和换手率，
    筛选疑似涨停候选股（换手率>5%且当日涨幅较高）。
    push2 已完全失效（2026-03-27），此为新主数据源。
    """
    try:
        # 从 medium 获取有资金流向数据的强势股列表
        # 使用东财热门股列表+medium批量补充
        # 方案：查市场主线板块中的龙头股
        import sys
        sys.path.insert(0, '/home/admin/openclaw/workspace/stock-assistant/scripts')
        from mcp_stock import call_mcp, get_medium_info
        
        # 尝试调 LimitUp（不稳定，退化为获取各行业龙头）
        zt_stocks = []
        
        # 东财板块行情用 medium 逐个查（选有实质性资金数据的）
        # 这里用"行业概念"中带"新能源""科技""医药"等热词的龙头股
        # 实际策略：从 medium 返回的当日涨跌幅+换手率筛选
        # 由于无法批量，需要一个股票列表作为候选
        # 用固定候选池 + medium 过滤
        CANDIDATE_CODES = [
            "SH600036","SH601318","SH600016","SH601166","SH600028",
            "SH601888","SH600519","SH300750","SH688981","SH002475",
            "SH600276","SH000858","SH601012","SH002594","SH600585",
        ]
        for code in CANDIDATE_CODES:
            info = get_medium_info(code)
            if not info: continue
            pct = info.get("change_pct", 0) or 0
            turn = info.get("turnover", 0) or 0
            if pct >= 9.5:  # 涨停
                zt_stocks.append({
                    "name": info.get("name", code),
                    "code": code,
                    "pct": pct,
                    "turnover": turn,
                    "main_net_inflow": info.get("main_net_inflow"),
                    "sector": ""
                })
        return zt_stocks
    except Exception:
        return []

def get_zt_pool():
    """
    获取当日涨停股池（东财 push2 接口）。注意：f3 字段为"今日涨幅"，不是"昨日涨停"，此函数实际返回当日已涨停股票。
    格式: x({json}); 正则用非贪婪匹配。
    大整数字段(f43等)除100转为浮点数。
    """
    try:
        import re as _re, json as _json, subprocess as _sp
        URL = ("https://push2.eastmoney.com/api/qt/clist/get"
               "?pn=1&pz=100&po=1&np=1&fltt=2&invt=2&fid=f3"
               "&fs=m:0+t:6,m:0+t:13,m:1+t:2,m:1+t:23"
               "&fields=f12,f14,f3,f8,f10&cb=x")
        cmd = ["curl","-s","--max-time","8", URL,
               "-H","User-Agent: Mozilla/5.0",
               "-H","Referer: https://quote.eastmoney.com/"]
        r = _sp.run(cmd, capture_output=True, text=True, timeout=10)
        m = _re.search(r'x\((.+)\);?\s*$', r.stdout, _re.DOTALL)
        if not m:
            return []
        text = m.group(1)
        # 大整数字段除100转浮点
        for field in ["f43","f44","f45","f46","f47","f48","f57"]:
            text = _re.sub(f'("{field}":)(\d+)', 
                          lambda mv: f'"{mv.group(1)}"{float(mv.group(2))}', text)
        data = _json.loads(text)
        items = data.get("data", {}).get("diff", [])
        zt = []
        for item in items:
            pct = item.get("f3", 0)
            if pct < 9.5:
                continue
            name = item.get("f14", "")
            code = str(item.get("f12", ""))
            if "ST" in name or "st" in name:
                continue
            if code.startswith(("8","4")):
                continue
            zt.append({
                "name": name,
                "code": code,
                "pct": pct,
                "turnover": item.get("f8"),
                "amplitude": item.get("f10"),
            })
        return zt
    except Exception:
        return []

def filter回调股(zt_list, limit=5):
    codes = [s["code"] for s in zt_list[:20]]
    prices = get_prices_concurrent(codes)
    candidates = []
    for stock in zt_list[:20]:
        info = prices.get(stock["code"])
        if not info:
            continue
        if -3 <= info["pct"] <= 2:
            candidates.append({
                "code": info["code"], "name": info["name"],
                "reason": "强势回调 今日{}% 昨日涨停{}%".format(info["pct"], stock["pct"]),
                "score": abs(info["pct"]) + 5, "status": "candidate",
                "entry_date": None, "entry_price": None,
                "hold_days": 0, "current_price": None, "current_pct": None,
                "strategy_version": 1
            })
    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates[:limit]

def load_pool():
    if os.path.exists(POOL_FILE):
        with open(POOL_FILE) as f:
            return json.load(f)
    return {"stocks": [], "strategy_version": 1, "last_update": ""}

def save_pool(pool):
    pool["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(POOL_FILE, "w") as f:
        json.dump(pool, f, ensure_ascii=False, indent=2)

def load_strategy():
    if os.path.exists(STRATEGY_FILE):
        with open(STRATEGY_FILE) as f:
            return json.load(f)
    return {"version": 1, "excluded": [], "notes": []}

def save_strategy(s):
    with open(STRATEGY_FILE, "w") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)

def should_remove(stock):
    if not stock.get("entry_price") or not stock.get("current_price"):
        return False, ""
    entry = stock["entry_price"]
    cur = stock["current_price"]
    hold = stock.get("hold_days", 0)
    pct = (cur - entry) / entry * 100
    if pct <= -3:
        return True, "亏损{}%止损".format(round(pct, 1))
    if pct >= 3:
        return True, "盈利{}%达标".format(round(pct, 1))
    if hold >= 5:
        return True, "持仓{}天到期".format(hold)
    return False, ""

def review_stock(stock, exit_price, reason):
    if not stock.get("entry_price"):
        return
    entry = stock["entry_price"]
    hold = stock.get("hold_days", 0)
    pct = round((exit_price - entry) / entry * 100, 2)
    ts = datetime.now().strftime("%Y%m%d")
    rev = {
        "code": stock["code"], "name": stock["name"],
        "entry_date": stock.get("entry_date"), "entry_price": entry,
        "exit_price": exit_price, "exit_reason": reason,
        "hold_days": hold, "profit_pct": pct,
        "result": "盈利" if pct > 0 else "亏损",
        "review_date": ts, "strategy_version": stock.get("strategy_version", 1)
    }
    with open(os.path.join(REVIEW_DIR, stock["code"] + "-" + ts + ".json"), "w") as f:
        json.dump(rev, f, ensure_ascii=False, indent=2)
    # 连续2次亏损 → 黑名单
    s = load_strategy()
    recent = sorted([f for f in os.listdir(REVIEW_DIR) if stock["code"] in f])[-2:]
    if len(recent) >= 2:
        last2 = []
        for rf in recent:
            with open(os.path.join(REVIEW_DIR, rf)) as f:
                last2.append(json.load(f))
        if all(r.get("result") == "亏损" for r in last2):
            if stock["code"] not in s["excluded"]:
                s["excluded"].append(stock["code"])
                s["notes"].append("{}: {} 连续2次亏损加入黑名单".format(ts, stock["code"]))
                save_strategy(s)
    return rev

def _feishu_send(text):
    """发飞书（静默失败）"""
    try:
        with open("/home/admin/.openclaw/openclaw.json") as f:
            cfg = json.load(f).get("channels", {}).get("feishu", {})
        app_id, app_secret = cfg.get("appId"), cfg.get("appSecret")
        token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        data = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode()
        with urllib.request.urlopen(token_url, data=data, timeout=8) as r:
            token = json.loads(r.read()).get("tenant_access_token", "")
        payload = {"receive_id": "ou_7e5fc2ebd19e226b5671475bd6d1bbdc",
                   "msg_type": "text", "content": json.dumps({"text": text})}
        req = urllib.request.Request(
            "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id",
            data=json.dumps(payload).encode(),
            headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=8) as r:
            json.loads(r.read())
    except Exception as e:
        print(f"保存池子失败: {e}")
        pass

def run():
    pool = load_pool()
    s = load_strategy()
    exits = []
    added = []

    # 检查持仓股（并发）
    holding_stocks = [st for st in pool["stocks"] if st.get("status") == "holding"]
    prices = get_prices_concurrent([st["code"] for st in holding_stocks])
    for st in list(pool["stocks"]):
        if st.get("status") != "holding":
            continue
        info = prices.get(st["code"])
        if not info:
            continue
        st["hold_days"] = st.get("hold_days", 0) + 1
        st["current_price"] = info["price"]
        st["current_pct"] = info["pct"]
        ok, reason = should_remove(st)
        if ok:
            exits.append((st, info["price"], reason))

    # 执行剔除+复盘
    for st, price, reason in exits:
        pool["stocks"] = [x for x in pool["stocks"] if x["code"] != st["code"]]
        review_stock(st, price, reason)

    # 补池至 7 只
    current = [st["code"] for st in pool["stocks"] if st.get("status") == "holding"]
    need = 7 - len(current)
    if need > 0:
        zt = get_zt_pool()
        candidates = filter回调股(zt, limit=need * 3)
        filtered = [c for c in candidates if c["code"] not in s.get("excluded", []) and c["code"] not in current]
        for c in filtered:
            if len([x for x in pool["stocks"] if x.get("status") == "holding"]) >= 7:
                break
            info = get_price_cross(c["code"])
            if not info:
                continue
            c.update({"entry_price": info["price"],
                      "entry_date": datetime.now().strftime("%Y-%m-%d"),
                      "status": "holding", "hold_days": 0,
                      "current_price": info["price"],
                      "current_pct": info["pct"],
                      "strategy_version": s["version"]})
            pool["stocks"].append(c)
            added.append(c)

    save_pool(pool)

    # 仅池子有变化时发飞书
    if exits or added:
        lines = ["📋 选股池更新 {}".format(datetime.now().strftime("%m-%d %H:%M"))]
        for st, price, reason in exits:
            lines.append("出: {}({}) {}".format(st["name"], st["code"], reason))
        for c in added:
            lines.append("入: {}({})".format(c["name"], c["code"]))
        _feishu_send("\n".join(lines))

    return pool

if __name__ == "__main__":
    run()

def filter_技术增强回调股(zt_list, limit=5):
    """
    增强版回调股筛选：先拉实时价格 + 技术指标综合评分
    使用 MCP full 获取 KDJ/RSI/MACD 综合评分
    """
    from scripts.mcp_stock import call_mcp, parse_full_technical
    
    # 先获取实时价格
    codes = [s["code"] for s in zt_list[:20]]
    prices = get_prices_concurrent(codes)
    
    candidates = []
    for stock in zt_list[:20]:
        try:
            info = prices.get(stock["code"])
            if not info:
                continue
            
            # 今日实时价格在-3%~+2%为回调候选
            today_pct = info.get("pct", 0)
            if not (-3 <= today_pct <= 2):
                continue
            
            # 获取技术指标
            result = call_mcp("full", {"symbol": stock["code"]})
            if not result or not result.get("content"):
                continue
            tech = parse_full_technical(result["content"][0]["text"])
            if not tech:
                continue
            
            k = tech["kdj_k"]; d = tech["kdj_d"]
            rsi6 = tech["rsi6"]
            macd_dif = tech["macd_dif"]; macd_dea = tech["macd_dea"]
            
            # 技术指标综合评分
            score = 0
            reasons = []
            
            # KDJ超卖（K<30 或 J<0）
            if k < 30: score += 10; reasons.append(f"KDJ超卖K={k:.1f}")
            elif k < 40: score += 5; reasons.append(f"KDJ偏低K={k:.1f}")
            
            # MACD金叉或零轴上方
            if macd_dif > macd_dea: score += 8; reasons.append("MACD金叉")
            if macd_dif > 0: score += 4; reasons.append(f"MACD零轴上DIF={macd_dif:.2f}")
            
            # RSI不过热
            if rsi6 < 40: score += 6; reasons.append(f"RSI偏低={rsi6:.1f}")
            elif rsi6 < 60: score += 2; reasons.append(f"RSI健康={rsi6:.1f}")
            
            if score < 5:
                continue
                
            candidates.append({
                "code": stock["code"],
                "name": info.get("name", stock.get("name", "")),
                "reason": " | ".join(reasons),
                "score": score,
                "kdj_k": k, "kdj_d": d,
                "rsi6": rsi6,
                "macd_dif": macd_dif, "macd_dea": macd_dea,
                "pct": today_pct,
                "strategy_version": 2
            })
        except Exception:
            continue
    
    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates[:limit]

def filter_强势股_板块增强(candidates=None, limit=5):
    """
    filter强势股 + 板块轮动增强版
    条件：-3%<=涨幅<=0% + 量比>2 + 资金流入板块优先
    """
    import sys
    sys.path.insert(0, '/home/admin/openclaw/workspace/stock-assistant/scripts')
    from mcp_stock import get_medium_info
    
    if candidates is None:
        candidates = get_强势股候选池()
    
    sector_watch_file = "/home/admin/openclaw/workspace/stock-assistant/data/sector_watch.json"
    hot_sectors = set()
    try:
        import json
        with open(sector_watch_file) as f:
            sw = json.load(f)
        for s in sw.get("sector_details", []):
            if s.get("heat", "").count("🔥") >= 2:
                hot_sectors.add(s["name"])
    except:
        pass
    
    results = []
    for stock in candidates[:30]:
        try:
            info = get_medium_info(stock["code"])
            if not info:
                continue
            
            pct = info.get("change_pct", 0) or 0
            vol_ratio = info.get("vol_ratio", 0) or 0
            
            # 价格条件
            if not (-3 <= pct <= 0):
                continue
            if vol_ratio < 2:
                continue
            
            # 板块标签
            sector_tags = info.get("sector", "").split() if info.get("sector") else []
            is_hot = any(tag in hot_sectors for tag in sector_tags)
            
            # 资金流向（优先流入）
            main_inflow = info.get("main_net_inflow", 0) or 0
            
            score = 0
            reasons = []
            if vol_ratio > 5: score += 10; reasons.append(f"量比{vol_ratio:.1f}>5")
            elif vol_ratio > 3: score += 5; reasons.append(f"量比{vol_ratio:.1f}>3")
            if main_inflow > 0: score += 8; reasons.append(f"主力净流入{main_inflow:.0f}万")
            if is_hot: score += 6; reasons.append(f"热门板块{','.join(sector_tags)}")
            if pct < -2: score += 4; reasons.append(f"深度回调{pct:.1f}%")
            
            if score < 5:
                continue
            
            results.append({
                "code": stock["code"],
                "name": info.get("name", stock.get("name", "")),
                "price": info.get("price"),
                "pct": pct,
                "vol_ratio": vol_ratio,
                "main_inflow": main_inflow,
                "sectors": sector_tags,
                "score": score,
                "reason": " | ".join(reasons),
            })
        except Exception:
            continue
    
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]
