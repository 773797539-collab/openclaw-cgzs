#!/usr/bin/env python3
# update-system-json.py - 更新门户 system.json
# 用途：cron 每日运行，更新 system.json 中的动态字段

import json
import os
from datetime import datetime, timedelta

SYSTEM_JSON = "/home/admin/openclaw/workspace/portal/status/system.json"
TASKS_JSON = "/home/admin/openclaw/workspace/portal/status/tasks.json"
TASKS_DIR = "/home/admin/openclaw/workspace/stock-assistant/tasks"

def count_tasks():
    counts = {"todo": 0, "doing": 0, "done": 0, "blocked": 0, "approval": 0}
    for pool in counts:
        path = os.path.join(TASKS_DIR, pool)
        if os.path.isdir(path):
            counts[pool] = len([f for f in os.listdir(path) if f.endswith(".md")])
    return counts

def read_task_detail(pool):
    """读取任务池中的任务详情"""
    path = os.path.join(TASKS_DIR, pool)
    tasks = []
    if os.path.isdir(path):
        for f in sorted(os.listdir(path)):
            if f.endswith(".md"):
                tasks.append({"id": f.replace(".md",""), "name": f.replace(".md","").replace("TASK-","任务-")})
    return tasks

def main():
    if not os.path.exists(SYSTEM_JSON):
        print(f"❌ {SYSTEM_JSON} not found")
        return

    with open(SYSTEM_JSON, "r") as f:
        data = json.load(f)

    data["lastUpdated"] = datetime.now().isoformat() + "+08:00"
    task_counts = count_tasks()
    data["taskPool"] = task_counts

    backup_dir = "/home/admin/openclaw/workspace/backups"
    if os.path.isdir(backup_dir):
        files = sorted([f for f in os.listdir(backup_dir) if f.endswith(".tar.gz")])
        if files:
            latest = files[-1]
            data["backup"]["last"] = {
                "time": latest.replace(".tar.gz","").replace("T"," ").replace("-",":"),
                "file": os.path.join(backup_dir, latest),
                "status": "verified"
            }

    with open(SYSTEM_JSON, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ system.json updated at {data['lastUpdated']}")
    print(f"   taskPool: {task_counts}")
    print(f"   (tasks.json 由 process_inbox.py 维护，此脚本只更新 system.json)")

if __name__ == "__main__":
    main()
