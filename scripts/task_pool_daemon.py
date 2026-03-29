#!/usr/bin/env python3
"""task_pool_daemon.py - 任务池常驻执行器（纯Python）"""
import subprocess
import time
import os
import json
import signal
import sys

WORKSPACE = "/home/admin/openclaw/workspace"
DAEMON_LOG = "/tmp/task_pool_daemon.log"
API_KEY = "sk-cp-B-h-RjQvCGBUCL42doqN1zKJMqhUx1McK-23ceE0nk7WAkHVzqby80U9S2TL6fjQUTolm7aobtX9squzXW5Vsoc-mUYK32RS9ohNwmruEg6vcfU0TjPjTi0"

def log(msg):
    ts = time.strftime("%H:%M:%S")
    line = f"[daemon {ts}] {msg}"
    print(line, flush=True)
    with open(DAEMON_LOG, "a") as f:
        f.write(line + "\n")

def get_token():
    try:
        r = subprocess.run([
            "curl", "-s",
            "https://www.minimaxi.com/v1/api/openplatform/coding_plan/remains",
            "-H", f"Authorization: Bearer {API_KEY}",
            "-H", "Content-Type: application/json"
        ], capture_output=True, text=True, timeout=10)
        data = json.loads(r.stdout)
        for m in data.get("model_remains", []):
            if "MiniMax-M*" in m.get("model_name", ""):
                return m["current_interval_usage_count"]
        return None
    except:
        return None

def run_task():
    r = subprocess.run(
        ["python3", f"{WORKSPACE}/scripts/internal_task_pool.py"],
        capture_output=True, text=True, timeout=60,
        cwd=WORKSPACE
    )
    return r.returncode == 0, r.stdout.strip()[:100]

def main():
    log("任务池 daemon 启动")
    tick = 0
    while True:
        tick += 1
        token = get_token()
        
        if token is None:
            log(f"tick#{tick} Token=API失败，继续")
        elif token == 0:
            log(f"tick#{tick} Token=0，退出")
            break
        else:
            log(f"tick#{tick} Token={token}，执行任务")
            ok, out = run_task()
            if ok:
                log(f"tick#{tick} 任务完成: {out}")
            else:
                log(f"tick#{tick} 任务失败: {out}")
        
        time.sleep(30)  # 30秒间隔

if __name__ == "__main__":
    main()
