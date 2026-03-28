#!/usr/bin/env python3
"""
止损止盈监控脚本
每小时半点自动运行（通过 cron）
持仓浮亏超过止损线或浮盈达到止盈线时，发送飞书通知
同一价格只报警一次，避免重复轰炸
"""
import os, json, re, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

FEISHU_USER = "ou_7e5fc2ebd19e226b5671475bd6d1bbdc"
PORTFOLIO_JSON = "/home/admin/openclaw/workspace/portal/status/portfolio.json"
CONFIG_PATH = "/home/admin/openclaw/workspace/stock-assistant/data/alert_config.json"
LOG_PATH = "/home/admin/openclaw/workspace/stock-assistant/data/alert_log.json"
MCP_URL = "http://82.156.17.205/cnstock/mcp"

DEFAULT_STOP_LOSS = -8.0    # 默认止损线 -8%
DEFAULT_TAKE_PROFIT = 10.0   # 默认止盈线 +10%

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH) as f:
                return json.load(f)
        except: pass
    return {"default": {"stop_loss": DEFAULT_STOP_LOSS, "take_profit": DEFAULT_TAKE_PROFIT}}

def feishu_send(text):
    """发送飞书消息"""
    try:
        with open("/home/admin/.openclaw/openclaw.json") as f:
            cfg = json.load(f).get("channels", {}).get("feishu", {})
        app_id = cfg.get("appId"); app_secret = cfg.get("appSecret")
        token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        token_data = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode()
        token_req = __import__('urllib.request').Request(token_url, data=token_data, headers={"Content-Type": "application/json"})
        with __import__('urllib.request').urlopen(token_req, timeout=10) as r:
            token = json.loads(r.read()).get("tenant_access_token", "")
        msg_url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
        payload = {"receive_id": FEISHU_USER, "msg_type": "text", "content": json.dumps({"text": text})}
        msg_req = __import__('urllib.request').Request(msg_url, data=json.dumps(payload).encode(), headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        with __import__('urllib.request').urlopen(msg_req, timeout=10) as r:
            return json.loads(r.read()).get("code") == 0
    except Exception as e:
        print(f"飞书发送失败: {e}")
        return False

def get_price_mcp(code):
    """MCP获取个股现价（主力）+ 涨跌"""
    try:
        normalized = ("SH" if code.startswith("6") else "SZ") + code
        payload = {"jsonrpc":"2.0","method":"tools/call","params":{"name":"brief","arguments":{"symbol":normalized}},"id":1}
        req = urllib.request.Request(MCP_URL, data=json.dumps(payload).encode(),
            headers={"Content-Type":"application/json","Accept":"application/json, text/event-stream"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = resp.read().decode()
        idx = raw.find("data:")
        if idx < 0: return None, None
        result = json.loads(raw[idx+5:].strip()).get("result",{})
        text = ""
        if isinstance(result.get("content"), list):
            for item in result["content"]:
                if isinstance(item, dict) and item.get("type") == "text":
                    text = item.get("text",""); break
        if not text: return None, None
        price = pct = None
        in_price = False
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("## 价格"): in_price = True
            elif line.startswith("##"): in_price = False
            if in_price and "当日:" in line and "%" not in line:
                mv = re.search(r'当日:\s*([\d.]+)', line)
                if mv and price is None: price = float(mv.group(1))
            if not in_price and "当日:" in line and "%" in line:
                mv = re.search(r'当日:\s*([+-]?[\d.]+)%', line)
                if mv: pct = float(mv.group(1))
        return price, pct
    except:
        return None, None

def check_and_alert():
    config = load_config()
    log = {"last_check": "", "alerts": [], "history": []}
    _last_alert_keys = {}
    if os.path.exists(LOG_PATH):
        try:
            with open(LOG_PATH) as f:
                old = json.load(f)
                log["history"] = old.get("history", []) or []
                # 提取所有 _last_alert 键（用于去重，不丢失）
                for k, v in old.items():
                    if k.startswith("_last_alert"):
                        _last_alert_keys[k] = v
        except Exception as e:
            print(f"读取日志失败: {e}")

    if not os.path.exists(PORTFOLIO_JSON):
        return []

    with open(PORTFOLIO_JSON) as f:
        portfolio = json.load(f)

    alerts = []
    now = ""
    try:
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
    except:
        pass
    log["last_check"] = now

    def check_holding(h):
        code, name = h["code"], h["name"]
        cost = h.get("cost")
        price, chg = get_price_mcp(code)
        if price is None or cost is None:
            return None
        profit_pct = round((price - cost) / cost * 100, 2)
        stock_cfg = config.get(code, config.get("default", {}))
        stop_loss = stock_cfg.get("stop_loss", DEFAULT_STOP_LOSS)
        take_profit = stock_cfg.get("take_profit", DEFAULT_TAKE_PROFIT)
        triggered = None
        if profit_pct <= stop_loss:
            triggered = f"🔴 止损触发！{name}({code}) 现价¥{price}（-{abs(profit_pct):.1f}%）跌破成本¥{cost}的{abs(stop_loss)}%止损线"
        elif profit_pct >= take_profit:
            triggered = f"🟢 止盈触发！{name}({code}) 现价¥{price}（+{profit_pct:.1f}%）触及成本¥{cost}的+{take_profit}%止盈线"
        if triggered:
            last_key = f"{code}_last_alert"
            return (triggered, last_key, f"{profit_pct:.1f}")
        return None

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(check_holding, h): h for h in portfolio.get("holdings", [])}
        for future in as_completed(futures):
            result = future.result()
            if result:
                triggered, last_key, val = result
                if log.get(last_key) != val:
                    alerts.append(triggered)
                    log[last_key] = val
                    feishu_send(triggered)

    log["alerts"] = alerts
    if alerts:
        log["history"].insert(0, {"time": now, "alerts": alerts})
        log["history"] = log["history"][:10]
    # 合并 _last_alert_keys 到 log 再保存（下次启动恢复去重状态）
    for k, v in _last_alert_keys.items():
        log[k] = v

    with open(LOG_PATH, "w") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

    return alerts

def is_market_open():
    """检查当前是否在交易时间内（周一至周五 09:00-15:30）"""
    from datetime import datetime, time
    now = datetime.now()
    if now.weekday() >= 5:
        return False
    t = now.time()
    return time(9, 0) <= t <= time(15, 30)

if __name__ == "__main__":
    import sys
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    config_path = CONFIG_PATH
    for i, arg in enumerate(sys.argv):
        if arg == "--config" and i+1 < len(sys.argv):
            config_path = sys.argv[i+1]
            break
    if dry_run:
        from datetime import datetime
        print("=== stop_loss_monitor dry-run 模式 ===")
        print(f"当前: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"市场开放: {is_market_open()}")
        if not is_market_open():
            print("（收盘后/周末，实际不检查止损）")
            sys.exit(0)
        print("（实际执行止损检查并推送飞书）")
        sys.exit(0)
    elif not is_market_open():
        print("收盘后不检查止损")
        sys.exit(0)
    result = check_and_alert()
    if result:
        for a in result:
            print(f"ALERT: {a}")
    else:
        print("无预警")
