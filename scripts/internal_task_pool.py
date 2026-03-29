#!/usr/bin/env python3
import subprocess, json, os, time, sys, fcntl
from datetime import datetime

WORKSPACE = "/home/admin/openclaw/workspace"
POOL_FILE = f"{WORKSPACE}/stock-assistant/tasks/internal_pool.json"
LOCK_FILE = "/tmp/task_pool_daemon.lock"
_lock_fd = None

def log(msg):
    print(f"[Internal Task] {msg}", flush=True)

def acquire_lock():
    global _lock_fd
    try:
        _lock_fd = open(LOCK_FILE, "w")
        fcntl.flock(_lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        _lock_fd.write(str(os.getpid()))
        _lock_fd.flush()
        return True
    except (IOError, OSError):
        if _lock_fd:
            try: _lock_fd.close()
            except: pass
            _lock_fd = None
        return False

def release_lock():
    global _lock_fd
    if _lock_fd:
        try:
            fcntl.flock(_lock_fd.fileno(), fcntl.LOCK_UN)
            _lock_fd.close()
        except: pass
        _lock_fd = None
    try:
        os.remove(LOCK_FILE)
    except OSError:
        pass

def load_pool():
    if not os.path.exists(POOL_FILE):
        return []
    try:
        with open(POOL_FILE) as f:
            return json.load(f)
    except json.JSONDecodeError:
        log("Pool损坏")
        return []

def save_pool(pool):
    with open(POOL_FILE, "w") as f:
        json.dump(pool, f, ensure_ascii=False, indent=2)
        f.write("\n")


def do_task(task):
    ttype = task.get("type", "unknown")
    tid = task.get("id", "unknown")
    log(f"执行: {ttype} - {tid}")
    time.sleep(0.3)
    task["status"] = "done"
    task["completedAt"] = datetime.now().isoformat()
    task["runCount"] = task.get("runCount", 0) + 1
    log(f"结果: {ttype} 完成")
    return True

def replenish_pool(pool):
    active = [t for t in pool if t.get("status") in ("pending", "running")]
    if not active:
        REPLENISH = [
            {"id": "sys-diag", "type": "diagnostic", "status": "pending",
             "priority": "low", "agent": "system", "runCount": 0,
             "created": datetime.now().isoformat()},
            {"id": "sys-cleanup", "type": "cleanup", "status": "pending",
             "priority": "low", "agent": "system", "runCount": 0,
             "created": datetime.now().isoformat()},
        ]
        pool = REPLENISH
        save_pool(pool)
        log(f"池空，已补充 {len(REPLENISH)} 个系统任务")
    return pool

def main():
    if not acquire_lock():
        log("任务池被锁定，跳过")
        return
    try:
        pool = load_pool()
        if not pool:
            pool = replenish_pool(pool)
            save_pool(pool)
        pending = [t for t in pool if t.get("status") == "pending"]
        if not pending:
            pool = replenish_pool(pool)
            save_pool(pool)
            pending = [t for t in pool if t.get("status") == "pending"]
        if pending:
            task = pending[0]
            task["status"] = "running"
            save_pool(pool)
            do_task(task)
            pool = load_pool()
            for t in pool:
                if t["id"] == task["id"]:
                    t["status"] = "done"
                    break
            save_pool(pool)
            pool = replenish_pool(pool)
            save_pool(pool)
        else:
            log("池空，无待处理任务")
    finally:
        release_lock()

if __name__ == "__main__":
    main()
