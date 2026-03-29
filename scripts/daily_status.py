#!/usr/bin/env python3
"""
daily_status.py - 每日系统状态汇总（一次性脚本）
输出当前系统关键指标，供 heartbeat 或人工查看
"""
import subprocess, json, os, sys
from datetime import datetime

WORKSPACE = "/home/admin/openclaw/workspace"

def cmd(c):
    r = subprocess.run(c, shell=True, capture_output=True, text=True)
    return r.stdout.strip(), r.returncode

def git_status():
    out, _ = cmd(f"cd {WORKSPACE} && git log --oneline -1")
    return out

def token_status():
    API_KEY = "sk-cp-B-h-RjQvCGBUCL42doqN1zKJMqhUx1McK-23ceE0nk7WAkHVzqby80U9S2TL6fjQUTolm7aobtX9squzXW5Vsoc-mUYK32RS9ohNwmruEg6vcfU0TjPjTi0"
    r = subprocess.run([
        "curl", "-s",
        "https://www.minimaxi.com/v1/api/openplatform/coding_plan/remains",
        "-H", f"Authorization: Bearer {API_KEY}",
        "-H", "Content-Type: application/json"
    ], capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)
        for m in d.get("model_remains", []):
            if "MiniMax-M*" in m.get("model_name", ""):
                A = m["current_interval_usage_count"]
                B = m["current_interval_total_count"]
                return f"{A}/{B} ({A/B*100:.1f}%)", A
        return "未找到主模型", None
    except:
        return "API失败", None

def portal_status():
    r = subprocess.run(["curl", "-s", "http://localhost:8081/api/status/all"],
        capture_output=True, text=True)
    if r.returncode != 0:
        return "DOWN", 0
    try:
        d = json.loads(r.stdout)
        g = d.get("governance", {})
        p = d.get("portfolio", {})
        h = (p.get("holdings") or [{}])[0]
        val = int(float(h.get("price", 0)) * h.get("shares", 0))
        return f"ok (agents={g.get('agent_count','?')})", val
    except:
        return "解析失败", 0

def pending_queue():
    qf = f"{WORKSPACE}/stock-assistant/tasks/pending_stock_main.json"
    if not os.path.exists(qf):
        return "0"
    with open(qf) as f:
        q = json.load(f)
    return str(len(q))

def main():
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    git = git_status()
    token_str, token_remain = token_status()
    portal_str, portfolio_val = portal_status()
    queue_len = pending_queue()

    print(f"=== 系统状态 {ts} ===")
    print(f"Git:    {git}")
    print(f"Token:  {token_str}")
    print(f"Portal: {portal_str}")
    print(f"Portfolio: ¥{portfolio_val}")
    print(f"Pending queue: {queue_len} 条")

    if token_remain is not None and token_remain == 0:
        print("⚠️ Token=0，静默停摆")

if __name__ == "__main__":
    main()
