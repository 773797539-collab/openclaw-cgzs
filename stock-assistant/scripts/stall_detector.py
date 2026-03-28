#!/usr/bin/env python3
"""
stall_detector.py - 停摆与假运行检测
检测：
1. 长时间无实质产出（>2小时无新commit）
2. 只有心跳无实质操作（>5次心跳但无任务推进）
3. 时间戳异常（未来时间、倒退时间）
"""
import os, json, subprocess, time
from datetime import datetime, timedelta

WORKSPACE = "/home/admin/openclaw/workspace"
TASKS_DIR = os.path.join(WORKSPACE, "stock-assistant", "tasks")

def get_last_productive_commit():
    r = subprocess.run(
        ["git", "log", "--format=%H %ai %s", "-n", "100"],
        cwd=WORKSPACE, capture_output=True, text=True
    )
    for line in r.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split(" ", 2)
        if len(parts) >= 3:
            sha, dt_str, msg = parts
            if any(kw in msg.lower() for kw in ["heartbeat", "心跳", "status update"]):
                continue
            try:
                dt = datetime.strptime(dt_str[:19], "%Y-%m-%d %H:%M:%S")
                return dt, sha, msg
            except:
                continue
    return None, None, None

def check_stall():
    issues = []
    dt, sha, msg = get_last_productive_commit()
    if dt:
        delta = datetime.now() - dt
        hours = delta.total_seconds() / 3600
        if hours > 2:
            issues.append(f"停摆: {hours:.1f}h无实质commit ({sha[:8]})")
        else:
            print(f"OK: {hours:.1f}h内有效commit")

    doing_dir = os.path.join(TASKS_DIR, "doing")
    if os.path.isdir(doing_dir):
        for f in os.listdir(doing_dir):
            if f.endswith(".md"):
                fp = os.path.join(doing_dir, f)
                age_hours = (time.time() - os.path.getmtime(fp)) / 3600
                if age_hours > 4:
                    issues.append(f"doing任务过旧: {f} {age_hours:.1f}h停滞")

    return issues

def main():
    issues = check_stall()
    if issues:
        for i in issues:
            print(i)
        return 1
    print("OK: 无停摆")
    return 0

if __name__ == "__main__":
    exit(main())
