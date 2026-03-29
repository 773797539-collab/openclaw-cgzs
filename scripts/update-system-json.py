#!/usr/bin/env python3
# update-system-json.py - 更新门户 system.json
# 用途：cron 每日运行，更新 system.json 中的动态字段

import json
import os
import subprocess
from datetime import datetime, timedelta

SYSTEM_JSON = "/home/admin/openclaw/workspace/portal/status/system.json"
TASKS_JSON = "/home/admin/openclaw/workspace/portal/status/tasks.json"
TASKS_DIR = "/home/admin/openclaw/workspace/stock-assistant/tasks"
API_KEY = "sk-cp-B-h-RjQvCGBUCL42doqN1zKJMqhUx1McK-23ceE0nk7WAkHVzqby80U9S2TL6fjQUTolm7aobtX9squzXW5Vsoc-mUYK32RS9ohNwmruEg6vcfU0TjPjTi0"

def get_token_status():
    """获取 MiniMax Token 状态"""
    try:
        result = subprocess.run([
            "curl", "-s",
            "https://www.minimaxi.com/v1/api/openplatform/coding_plan/remains",
            "-H", f"Authorization: Bearer {API_KEY}",
            "-H", "Content-Type: application/json"
        ], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout)
        if data.get("base_resp", {}).get("status_code") != 0:
            return None
        for m in data.get("model_remains", []):
            if "MiniMax-M*" in m.get("model_name", ""):
                remaining = m["current_interval_usage_count"]
                total = m["current_interval_total_count"]
                hours = m["remains_time"] / 1000 / 3600
                return {"remaining": remaining, "total": total,
                        "pct": remaining/total*100, "hours": hours}
        return None
    except:
        return None

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

    token = get_token_status()
    if token:
        data["token"] = {
            "remaining": token["remaining"],
            "total": token["total"],
            "pct": round(token["pct"], 1),
            "hours": round(token["hours"], 1),
            "status": "ok" if token["pct"] > 20 else "warning" if token["pct"] > 0 else "depleted"
        }
    else:
        data["token"] = {"status": "api_failed"}

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
    if token:
        print(f"   Token: {token['remaining']}/{token['total']} ({token['pct']}%) 约{token['hours']}h")
    else:
        print(f"   Token: API失败")

if __name__ == "__main__":
    main()
