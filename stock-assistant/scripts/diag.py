#!/usr/bin/env python3
"""系统诊断工具 - 快速检查所有关键组件状态"""
import os, sys, json, subprocess
from datetime import datetime

def check(name, ok, detail=""):
    status = "✅" if ok else "❌"
    print(f"{status} {name}: {detail}")

print(f"=== 系统诊断 {datetime.now().strftime('%H:%M:%S')} ===\n")

# 1. cron
r = subprocess.run(["ps","-p","148638","-o","pid","-h"], capture_output=True, text=True)
check("cron daemon", bool(r.stdout.strip()), "PID 148638" if r.stdout.strip() else "NOT running")

# 2. inbox cron log
log = "/tmp/inbox-cron.log"
if os.path.exists(log):
    with open(log) as f: lines = f.read().strip().split("\n")
    last = lines[-1] if lines else ""
    check("inbox-cron.log", "inbox-cron done" in last or "inbox-cron start" in last, last[:60])
else:
    check("inbox-cron.log", False, "NOT found")

# 3. inbox 积压
inbox_dir = "/home/admin/openclaw/workspace/stock-assistant/tasks/inbox"
if os.path.exists(inbox_dir):
    files = [f for f in os.listdir(inbox_dir) if f.endswith(".md")]
    check("inbox", len(files)==0, f"{len(files)} 个积压" if files else "无积压")
else:
    check("inbox", False, "目录不存在")

# 4. Git
r = subprocess.run(["git","log","--oneline","-1"], capture_output=True, text=True, cwd="/home/admin/openclaw/workspace")
check("Git", bool(r.stdout.strip()), r.stdout.strip()[:40])

# 5. workflow history
wf_file = "/home/admin/openclaw/workspace/portal/status/workflow_history.json"
if os.path.exists(wf_file):
    with open(wf_file) as f: d = json.load(f)
    ws = d.get("workflows", [])
    completed = [w for w in ws if w.get("status")=="completed"]
    running = [w for w in ws if w.get("status")=="running"]
    check("workflow", True, f"{len(completed)} 完成, {len(running)} 进行中")
else:
    check("workflow", False, "NOT found")

# 6. data目录JSON
data_dir = "/home/admin/openclaw/workspace/stock-assistant/data"
ok_count = 0
for fn in ["stock_pool.json","alert_config.json","alert_log.json","strategy.json","market_sectors.json"]:
    fp = os.path.join(data_dir, fn)
    if os.path.exists(fp):
        try:
            with open(fp) as f: json.load(f)
            ok_count += 1
        except: pass
check("data/ JSON", ok_count>=5, f"{ok_count}/5 文件有效")

print("\n诊断完成")
