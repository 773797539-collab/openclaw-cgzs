#!/usr/bin/env python3
"""
market_close_scan.py - 每日收盘扫描
每天 16:00 自动运行（cron）
生成收盘报告并存入 reports/ 目录
"""
import sys, os, json, subprocess, re, urllib.request
from datetime import datetime

sys.path.insert(0, '/home/admin/openclaw/workspace/stock-assistant/scripts')
from mcp_stock import get_stock_info

WATCHLIST = "/home/admin/openclaw/workspace/stock-assistant/data/watchlist.yaml"
PORTFOLIO = "/home/admin/openclaw/workspace/portal/status/portfolio.json"
REPORT_DIR = "/home/admin/openclaw/workspace/stock-assistant/reports"
MCP_URL = "http://82.156.17.205/cnstock/mcp"

# 东财 push2 收盘指数
def get_index(secid):
    url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields=f43,f57,f58,f169,f170,f171&ut=fa5fd1943c7b386f172d6893dbfba10b"
    req = urllib.request.Request(url, headers={
        "Referer": "https://quote.eastmoney.com/",
        "User-Agent": "Mozilla/5.0"
    })
    with urllib.request.urlopen(req, timeout=5) as resp:
        d = json.loads(resp.read()).get("data", {})
        price = d.get("f43", 0) / 100
        chg = d.get("f169", 0) / 100  # 涨跌额
        pct = d.get("f170", 0) / 100   # 涨跌幅
        name = d.get("f58", secid)
        return {"name": name, "price": price, "chg": chg, "pct": pct}

def read_watchlist():
    holdings = []
    if os.path.exists(WATCHLIST):
        with open(WATCHLIST) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"): continue
                parts = line.split("#")[0].strip().split()
                if len(parts) < 1: continue
                code = parts[0]
                shares = int(parts[1]) if len(parts) >= 2 else 0
                cost = float(parts[2]) if len(parts) >= 3 else 0
                holdings.append({"code": code, "shares": shares, "cost": cost})
    return holdings

def generate_close_report():
    now = datetime.now().strftime("%Y-%m-%d 16:05 GMT+8")
    lines = [f"# 每日收盘报告 - {now.split()[0]}", "", "## 一、大盘收盘", ""]

    indices = [
        ("上证指数", "1.000001"),
        ("深证成指", "0.399001"),
        ("创业板指", "0.399006"),
        ("科创50", "1.000688"),
    ]
    for name, secid in indices:
        try:
            idx = get_index(secid)
            pct = idx["pct"]
            sign = "+" if pct >= 0 else ""
            emoji = "🟢" if pct > 0 else ("🔴" if pct < 0 else "⚪")
            chg = idx.get('chg', 0)
            sign_c = "+" if chg >= 0 else ""
            lines.append(f"| {emoji} {name} | {idx['price']} | {sign_c}{chg:.2f} ({sign}{pct:.2f}%) |")
        except Exception as e:
            lines.append(f"| ❓ {name} | 获取失败 | - |")

    lines.append("")
    lines.append("## 二、持仓收盘状态")
    lines.append("")

    holdings = read_watchlist()
    if not holdings:
        lines.append("_无持仓数据_")
    else:
        for h in holdings:
            info = get_stock_info(h["code"])
            if not info or not info.get("price"):
                lines.append(f"- {h['code']}: 数据获取失败")
                continue
            price = info["price"]
            pct = info.get("change_pct", 0)
            cost = h["cost"]
            shares = h["shares"]
            mv = price * shares
            cv = cost * shares
            profit = mv - cv
            profit_pct = (price - cost) / cost * 100 if cost else 0
            sign1 = "+" if pct >= 0 else ""
            sign2 = "+" if profit_pct >= 0 else ""
            lines.append(f"- **{info.get('name', h['code'])}({h['code']})**")
            lines.append(f"  - 收盘价: ¥{price} ({sign1}{pct:.2f}%)")
            lines.append(f"  - 持仓: {shares}股，成本¥{cost}")
            lines.append(f"  - 市值: ¥{mv:.2f} | 盈亏: {sign2}¥{profit:.2f} ({sign2}{profit_pct:.1f}%)")
            lines.append("")

    lines.append("## 三、市场情绪与热点")
    lines.append("")
    # 基于今日大盘整体判断
    try:
        idx0 = get_index("1.000001")
        pct0 = idx0.get("pct", 0)
        if pct0 >= 1.0: sentiment = "🟢 强势上涨"
        elif pct0 >= 0.3: sentiment = "🟡 小幅上涨"
        elif pct0 >= -0.3: sentiment = "⚪ 震荡整理"
        elif pct0 >= -1.0: sentiment = "🟠 小幅下跌"
        else: sentiment = "🔴 弱势下跌"
        lines.append(f"今日市场: {sentiment}（上证 {pct0:+.2f}%）")
    except:
        lines.append("今日市场: 收盘数据获取失败")

    lines.append("")
    # 四、技术信号
    lines.extend(["", "## 五、持仓技术信号", ""])
    for h in holdings:
        info = get_stock_info(h["code"])
        if not info: continue
        try:
            import urllib.request as _urllib
            payload = {"jsonrpc":"2.0","method":"tools/call",
                       "params":{"name":"full","arguments":{"symbol":h["code"]}},"id":1}
            req = _urllib.Request(MCP_URL, data=json.dumps(payload).encode(),
                headers={"Content-Type":"application/json","Accept":"application/json, text/event-stream"})
            with _urllib.urlopen(req, timeout=8) as resp:
                raw = resp.read().decode()
            idx2 = raw.find("data:")
            if idx2 < 0: continue
            result = json.loads(raw[idx2+5:].strip()).get("result",{})
            text2 = result.get("content",[{}])[0].get("text","") if result.get("content") else ""
            if not text2: continue
            for line in text2.split("\n"):
                if "| " not in line or "2026-" not in line or line.strip().startswith("| ---"): continue
                parts = [p.strip() for p in line.split("|")]
                if len(parts) < 20 or parts[1].count("-") != 2: continue
                try:
                    ma5,ma30 = float(parts[2]),float(parts[4])
                    macd_d,macd_de = float(parts[10]),float(parts[11])
                    k = float(parts[7]); rsi6 = float(parts[12])
                    boll_u,boll_l = float(parts[15]),float(parts[17])
                    price = info["price"]
                    trend = "▲" if ma5 > ma30 else "▼"
                    macd_s = "▲" if macd_d > macd_de else "▼"
                    kdj_s = "超卖" if k < 20 else "超买" if k > 80 else "正常"
                    boll_pct = (price-boll_l)/(boll_u-boll_l)*100 if boll_u!=boll_l else 50
                    lines.append(f"- **{info.get('name', h['code'])}({h['code']})**: MA5{ma5:.2f}{trend}MA30{ma30:.2f} | MACD{macd_s}{macd_d:.2f}/{macd_de:.2f} | KDJ K={k:.0f}({kdj_s}) | RSI6={rsi6:.0f} | 布林{boll_pct:.0f}%")
                    break
                except: continue
        except: continue
    lines.append("")
    lines.append("---\n_由 OpenClaw 自动生成 | 仅供参考_")
    return "\n".join(lines)

def push_close_summary():
    """推送收盘简报摘要到飞书"""
    try:
        import urllib.request, json
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        report_file = f"{REPORT_DIR}/daily-close-{today}.md"
        if not os.path.exists(report_file):
            return
        with open(report_file) as f:
            report = f.read()
        # 提取前800字
        summary = report[:800]
        payload = {
            "receive_id": "ou_7e5fc2ebd19e226b5671475bd6d1bbdc",
            "msg_type": "text",
            "content": json.dumps({"text": f"📊 收盘报告 {today}\n\n{summary}"})
        }
        # 通过 openclaw message 工具发送（subprocess 调用 openclaw CLI）
        import subprocess
        cmd = [
            "openclaw", "message", "send",
            "--channel", "feishu",
            "--target", "ou_7e5fc2ebd19e226b5671475bd6d1bbdc",
            "--message", f"📊 收盘报告 {today}\n\n{summary}"
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if r.returncode == 0:
            print(f"飞书推送成功")
        else:
            print(f"飞书推送失败: {r.stderr[:100]}")
    except Exception as e:
        print(f"飞书推送异常: {e}")

def save_report():
    report = generate_close_report()
    today = datetime.now().strftime("%Y-%m-%d")
    report_file = f"{REPORT_DIR}/daily-close-{today}.md"
    os.makedirs(REPORT_DIR, exist_ok=True)
    with open(report_file, "w") as f:
        f.write(report)
    print(f"收盘报告已保存: {report_file}")
    print()
    print(report)
    push_close_summary()

def can_run():
    """判断是否需要生成收盘报告（非交易日退出）"""
    now = datetime.now()
    if now.weekday() >= 5:
        print(f"[{now.strftime('%H:%M:%S')}] 今日非交易日，跳过收盘报告")
        return False
    return True

if __name__ == "__main__":
    import sys
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    today = datetime.now().strftime("%Y-%m-%d")
    if dry_run:
        print("=== market_close_scan dry-run 模式 ===")
        print(f"当前: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"交易日: {datetime.now().weekday() < 5}")
        print(f"可运行: {can_run()}")
        print(f"输出路径: {REPORT_DIR}/daily-close-{today}.md")
        print("（实际不生成报告，不推送飞书）")
        sys.exit(0)
    elif can_run():
        save_report()
