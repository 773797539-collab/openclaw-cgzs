#!/usr/bin/env python3
"""
market_open_coord.py
cron → main 收到 systemEvent → main 执行本脚本
本脚本驱动 stock-exec → stock-review → 通知用户的完整链条
"""
import sys
import json
import subprocess
import os
from datetime import datetime

OPENCLAW_CMD = "openclaw"

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
            return {
                "price": d.get("price"),
                "change_pct": d.get("change_pct"),
                "name": data.get("name")
            }
    except:
        pass
    return None

def main():
    print(f"=== 开盘扫描协调链 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
    
    # 读取持仓
    watchlist = []
    wl_path = "/home/admin/openclaw/workspace/stock-assistant/data/watchlist.yaml"
    cost_map = {}
    if os.path.exists(wl_path):
        with open(wl_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("#")[0].strip().split()
                code_part = parts[0]
                if len(parts) >= 3:
                    cost = float(parts[2])
                elif len(parts) == 2:
                    cost = float(parts[1])
                else:
                    import re
                    comment = line.split("#")[1] if "#" in line else ""
                    m = re.search(r'(\d+\.?\d*)', comment)
                    cost = float(m.group(1)) if m else None
                if code_part:
                    info = get_stock_price(code_part)
                    if info:
                        info["code"] = code_part
                        info["cost"] = cost
                        if cost and info.get("price"):
                            info["profit_pct"] = round((info["price"] - cost) / cost * 100, 2)
                        watchlist.append(info)
                        cost_map[code_part] = cost
    
    # 指数数据（eastmoney API，秒回）
    indices = {}
    try:
        index_map = [("1.000001","上证指数"),("0.399001","深成指"),("0.399006","创业板"),("1.000688","科创50")]
        for secid, name in index_map:
            try:
                import urllib.request, json
                url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields=f43,f57,f58,f170,f136"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    d = json.loads(resp.read()).get("data", {})
                    indices[name] = {
                        "price": d.get("f43", 0) / 100,
                        "change_pct": d.get("f170", 0) / 100,
                        "volume": d.get("f136", 0) / 1e8
                    }
            except Exception as e:
                print(f"指数 {name} 获取失败: {e}")
    except Exception as e:
        print(f"指数获取失败: {e}")
    
    # 涨跌停统计
    try:
        import akshare as ak
        spot = ak.stock_zh_a_spot_em()
        zt_count = len(spot[spot["涨跌幅"]>=9.5])
        dt_count = len(spot[spot["涨跌幅"]<=-9.5])
    except:
        zt_count, dt_count = None, None
    
    # 组装结果
    result = {
        "timestamp": datetime.now().isoformat(),
        "indices": indices,
        "zt_count": zt_count,
        "dt_count": dt_count,
        "holdings": watchlist,
        "status": "ok" if indices else "partial"
    }
    
    # 写临时结果
    with open("/tmp/market-open-result.json", "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"数据获取完成: {len(indices)}个指数, {len(watchlist)}只持仓股")
    
    # 验收（stock-review 逻辑，这里内联）
    issues = []
    if len(indices) < 4:
        issues.append(f"指数数据不完整: 仅{len(indices)}/4")
    if zt_count is None:
        issues.append("涨跌停统计失败")
    if not watchlist:
        issues.append("持仓数据为空")
    
    review_result = {
        "passed": len(issues) == 0,
        "issues": issues,
        "reviewer": "stock-review",
        "timestamp": datetime.now().isoformat()
    }
    with open("/tmp/market-open-review.json", "w") as f:
        json.dump(review_result, f, ensure_ascii=False, indent=2)
    print(f"验收完成: {'通过' if review_result['passed'] else '有问题'}")
    for issue in issues:
        print(f"  - {issue}")
    
    return result, review_result

def send_report(result, review):
    """发送飞书开盘报告"""
    lines = [f"📊 **每日开盘扫描 {datetime.now().strftime('%Y-%m-%d %H:%M')}**\n"]
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
            chg = h.get("change_pct", 0)
            csign = "+" if chg >= 0 else ""
            lines.append(f"{h['name']}({h['code']}): ¥{h['price']} {csign}{chg}% 浮亏{sign}{pct}%")
    else:
        lines.append("\n暂无持仓")
    msg = "\n".join(lines)
    run(f'{OPENCLAW_CMD} msg main "{msg}"')
    print("飞书通知已发送")

if __name__ == "__main__":
    result, review = main()
    send_report(result, review)
    sys.exit(0 if review["passed"] else 1)
