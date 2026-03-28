#!/usr/bin/env python3
"""
queue_processor.py - HEARTBEAT.md 调用的队列处理器
从 pending_stock_main.json 读取 pending 任务，逐条派发，然后更新队列状态。

dispatcher.py 的 DISPATCHER_ID=stock-main，所以任何通过它派发的 workflow
dispatchedBy 都是 "stock-main"，与调用路径无关。

用法（由 HEARTBEAT.md 或 cron 调用）：
  python3 /home/admin/openclaw/workspace/stock-assistant/scripts/queue_processor.py
"""
import json, subprocess, sys, os
from datetime import datetime

QUEUE_FILE = "/home/admin/openclaw/workspace/stock-assistant/tasks/pending_stock_main.json"
DISPATCHER  = "/home/admin/openclaw/workspace/stock-assistant/scripts/dispatcher.py"

def load_queue():
    if not os.path.exists(QUEUE_FILE):
        return []
    with open(QUEUE_FILE) as f:
        return json.load(f)

def save_queue(queue):
    with open(QUEUE_FILE, "w") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)

def process_queue():
    queue = load_queue()
    changed = False
    for item in queue:
        if item.get("status") != "pending_dispatch":
            continue
        name    = item.get("name", "")
        content = item.get("content", "")[:500]
        tid     = item.get("id", "")

        print(f"派发任务: {tid} - {name}")
        try:
            result = subprocess.run(
                ["python3", DISPATCHER, "--dispatch", name, content],
                capture_output=True, text=True, timeout=60,
                cwd=os.path.dirname(DISPATCHER)
            )
            if result.returncode == 0:
                item["status"]        = "dispatched"
                item["dispatchedAt"]  = datetime.now().isoformat()
                item["dispatchResult"] = result.stdout.strip()[:200]
                print(f"  ✅ {result.stdout.strip()[:100]}")
            else:
                item["error"] = result.stderr.strip()[:200]
                print(f"  ❌ {result.stderr.strip()[:100]}")
            changed = True
        except Exception as e:
            item["error"] = str(e)[:200]
            print(f"  ❌ Exception: {e}")
            changed = True

    if changed:
        save_queue(queue)
        print(f"队列已更新（{len([x for x in queue if x.get('status')=='dispatched'])} 条已派发）")
    else:
        print("队列中无待派发任务")

if __name__ == "__main__":
    process_queue()
