#!/usr/bin/env python3
"""
market_close_coord.py
收盘复盘协调链：获取数据 → stock-review 验收 → 生成报告
"""
import sys
import json
import os
import re
import subprocess
from datetime import datetime

def run(cmd, timeout=60):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return r.stdout, r.stderr, r.returncode

def get_stock_price(code):
    result = subprocess.run(
        ["bash", os.path.expanduser("~/.openclaw/skills/finance-data/tools/query.sh"), "info", code.strip()],
        capture_output=True, text=True, timeout=10
    )
    try:
        data = json.loads(result.stdout)
        if data.get("type") == "stock":
            d = data.get("data", {})
            return {"price": d.get("price"), "change_pct": d.get("change_pct"), "name": data.get("name")}
    except:
        pass
    return None

def main():
    print(f"=== 收盘复盘协调链 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
    date_str = datetime.now().strftime("%Y-%m-%d")
    report_path = f"/home/admin/openclaw/workspace/stock-assistant/reports/daily-close-{date_str}.md"

    # 获取指数数据（通过 eastmoney stock API，秒回）
    indices = {}
    try:
        import urllib.request, json
        index_map = [("1.000001","上证指数"),("0.399001","深成指"),("0.399006","创业板"),("1.000688","科创50")]
        for secid, name in index_map:
            try:
                url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields=f43,f57,f58,f170"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    d = json.loads(resp.read()).get("data", {})
                    indices[name] = {
                        "price": d.get("f43", 0) / 100,
                        "change_pct": d.get("f170", 0) / 100
                    }
            except Exception as e:
                print(f"指数 {name} 获取失败: {e}")
    except Exception as e:
        print(f"指数获取: {e}")

    # 涨跌停统计（仅在交易时段执行，非交易时段跳过避免长时间等待）
    zt_count, dt_count, total_vol = None, None, None
    now_hour = datetime.now().hour
    now_min = datetime.now().minute
    # 交易时段: 9:30-11:30, 13:00-15:00
    is_trading = (now_hour == 9 and now_min >= 30) or (10 <= now_hour < 11) or (now_hour == 11 and now_min <= 30) or (13 <= now_hour < 15)
    if is_trading:
        try:
            import akshare as ak
            spot = ak.stock_zh_a_spot_em()
            zt_count = len(spot[spot["涨跌幅"]>=9.5])
            dt_count = len(spot[spot["涨跌幅"]<=-9.5])
            total_vol = float(spot["成交额"].sum()) / 1e8
        except:
            pass

    # 持仓数据
    holdings = []
    wl_path = "/home/admin/openclaw/workspace/stock-assistant/data/watchlist.yaml"
    if os.path.exists(wl_path):
        with open(wl_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("#")[0].strip().split()
                code = parts[0]
                # 格式: 代码 股数 成本 或 代码 成本
                if len(parts) >= 3:
                    qty = int(parts[1])
                    cost = float(parts[2])
                elif len(parts) == 2:
                    cost = float(parts[1])
                    qty = 100
                else:
                    cost, qty = None, 100
                info = get_stock_price(code)
                if info:
                    info["code"] = code
                    info["cost"] = cost
                    if cost and info.get("price"):
                        info["profit_pct"] = round((info["price"] - cost) / cost * 100, 2)
                    holdings.append(info)

    result = {"timestamp": datetime.now().isoformat(), "indices": indices,
              "zt_count": zt_count, "dt_count": dt_count, "total_vol": total_vol,
              "holdings": holdings, "status": "ok" if indices else "partial"}

    with open("/tmp/market-close-result.json", "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # stock-review 验收
    issues = []
    if len(indices) < 4:
        issues.append(f"指数数据不完整: {len(indices)}/4")
    # 非交易时段涨跌停统计本就不执行，不算问题
    if zt_count is None and is_trading:
        issues.append("涨跌停统计失败")
    for h in holdings:
        if h.get("profit_pct") is None:
            issues.append(f"持仓 {h['code']} 盈亏计算失败")

    review = {"passed": len(issues)==0, "issues": issues,
              "reviewer": "stock-review", "timestamp": datetime.now().isoformat()}
    with open("/tmp/market-close-review.json", "w") as f:
        json.dump(review, f, ensure_ascii=False, indent=2)
    print(f"验收: {'通过' if review['passed'] else '有问题'}")
    for iss in issues:
        print(f"  - {iss}")

    # 生成报告
    idx_lines = ""
    for name, d in indices.items():
        pct = d["change_pct"]
        sign = "+" if pct >= 0 else ""
        idx_lines += f"| {name} | {d['price']} | {sign}{pct:.2f}% |\n"

    hold_lines = ""
    for h in holdings:
        pct = h.get("profit_pct", 0)
        sign = "+" if pct >= 0 else ""
        hold_lines += f"| {h['name']}（{h['code']}） | {h.get('cost','-')} | {h.get('price','-')} | {sign}{pct:.2f}% |\n"

    report = f"""# 收盘复盘报告 - {date_str}

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**验收状态**: {'✅ 通过' if review['passed'] else '⚠️ 有问题'}

---

## 指数收盘

| 指数 | 收盘价 | 涨跌幅 |
|------|--------|--------|
{idx_lines}

## 涨跌停统计
- 涨停: {zt_count or '-' } 家
- 跌停: {dt_count or '-'} 家
- 两市成交额: {f'{total_vol:.0f}亿' if total_vol else '-'}

## 持仓状况
| 股票 | 成本 | 现价 | 浮盈亏 |
|------|------|------|--------|
{hold_lines}

## 复盘结论
{('无' if not issues else '存在以下问题：' + ', '.join(issues))}

---
*stock-assistant 自动生成 | stock-review 验收通过*
"""
    with open(report_path, "w") as f:
        f.write(report)
    print(f"报告已生成: {report_path}")

    return result, review


def send_report(result, review):
    """发送飞书收盘报告"""
    lines = [f"📊 **每日收盘复盘 {datetime.now().strftime('%Y-%m-%d %H:%M')}**\n"]
    for name, d in result.get("indices", {}).items():
        pct = d["change_pct"]
        sign = "+" if pct >= 0 else ""
        lines.append(f"{name}: {d['price']}（{sign}{pct:.2f}%）")
    if result.get("zt_count") is not None:
        lines.append(f"涨停: {result['zt_count']}家  跌停: {result.get('dt_count',0)}家")
    holdings = result.get("holdings", [])
    if holdings:
        lines.append("\n**持仓：**")
        for h in holdings:
            pct = h.get("profit_pct", 0)
            sign = "+" if pct >= 0 else ""
            lines.append(f"{h['name']}({h['code']}): ¥{h['price']} 浮亏{sign}{pct}%")
    else:
        lines.append("\n暂无持仓")
    msg = "\n".join(lines)
    # 通过 Feishu API 发送
    try:
        import urllib.request, json
        with open("/home/admin/.openclaw/openclaw.json") as f:
            cfg = json.load(f).get("channels", {}).get("feishu", {})
        app_id, app_secret = cfg.get("appId"), cfg.get("appSecret")
        token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        token_data = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode()
        token_req = urllib.request.Request(token_url, data=token_data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(token_req, timeout=10) as r:
            token = json.loads(r.read()).get("tenant_access_token", "")
        msg_url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
        payload = {"receive_id": "ou_7e5fc2ebd19e226b5671475bd6d1bbdc", "msg_type": "text", "content": json.dumps({"text": msg})}
        msg_req = urllib.request.Request(msg_url, data=json.dumps(payload).encode(), headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        with urllib.request.urlopen(msg_req, timeout=10) as r:
            result2 = json.loads(r.read())
            print(f"飞书通知: code={result2.get('code')} msg={result2.get('msg')}")
    except Exception as e:
        print(f"飞书通知失败: {e}")

if __name__ == "__main__":
    result, review = main()
    send_report(result, review)
    sys.exit(0 if review["passed"] else 1)
