#!/usr/bin/env python3
"""task_executor 单实例守护脚本"""
import os, sys, time, subprocess, fcntl, signal

LOCK_FILE = "/tmp/task_exec_single.lock"
PID_FILE  = "/tmp/task_exec_single.pid"

def write_pid(pid):
    with open(PID_FILE, "w") as f:
        f.write(str(pid))

def is_running(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False

def cleanup(signum, frame):
    try:
        os.unlink(LOCK_FILE)
        os.unlink(PID_FILE)
    except:
        pass
    sys.exit(0)

signal.signal(signal.SIGTERM, cleanup)
signal.signal(signal.SIGINT, cleanup)

# 获取锁
fd = open(LOCK_FILE, "w")
try:
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
except IOError:
    old_pid = open(PID_FILE).read().strip() if os.path.exists(PID_FILE) else "?"
    print(f"[task_exec] 已有实例 PID={old_pid}，退出")
    sys.exit(1)

fd.write(str(os.getpid()))
fd.flush()
write_pid(os.getpid())
print(f"[task_exec] 启动 PID={os.getpid()}")

# 清理锁文件退出时
import atexit
atexit.register(lambda: (os.unlink(LOCK_FILE), os.unlink(PID_FILE)))

# 持续运行 task_executor，死后重启
while True:
    proc = subprocess.Popen([sys.executable, "/home/admin/openclaw/workspace/scripts/task_executor.py"])
    print(f"[watchdog] task_exec PID={proc.pid} 启动")
    proc.wait()
    print(f"[watchdog] task_exec 退出码={proc.returncode}，3秒后重启")
    time.sleep(3)
