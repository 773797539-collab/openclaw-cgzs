#!/usr/bin/env python3
"""
portfolio_history.py - 记录持仓历史价格
每小时运行一次，将持仓快照写入历史文件
"""
import json
import os
from datetime import datetime

HISTORY_FILE = "/home/admin/openclaw/workspace/portal/status/portfolio_history.json"

def main():
    # 读取当前持仓快照
    portfolio_file = "/home/admin/openclaw/workspace/portal/status/portfolio.json"
    if not os.path.exists(portfolio_file):
        print("⚠️ portfolio.json 不存在，跳过")
        return

    try:
        with open(portfolio_file) as f:
            current = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"⚠️ portfolio.json 读取失败: {e}，跳过")
        return

    holdings = current.get("holdings", [])
    if not holdings:
        print("⚠️ 无持仓，跳过")
        return

    # 读取历史
    history = {}
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE) as f:
                history = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️ history 文件读取失败: {e}，重新创建")
            history = {}

    # 追加当前快照
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    for h in holdings:
        code = h.get("code")
        if not code:
            continue
        if code not in history:
            history[code] = {"name": h.get("name"), "cost": h.get("cost"), "prices": []}
        history[code]["prices"].append({
            "time": ts,
            "price": h.get("price"),
            "change_pct": h.get("change_pct"),
            "profit_pct": h.get("profit_pct")
        })
        # 只保留最近30天
        history[code]["prices"] = history[code]["prices"][-720:]  # 每小时一条，保留30天

    # 写回
    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except IOError as e:
        print(f"⚠️ history 文件写入失败: {e}")
        return

    print(f"✅ 持仓历史已记录: {len(holdings)} 只股票")
    for h in holdings:
        code = h.get("code")
        count = len(history.get(code, {}).get("prices", []))
        print(f"   {h.get('name')} ({code}): {count} 条历史记录")

if __name__ == "__main__":
    main()
