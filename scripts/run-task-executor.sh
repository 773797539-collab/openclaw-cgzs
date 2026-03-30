#!/bin/bash
# run-task-executor.sh - 单一 task_executor 进程管理
LOCK="/tmp/task_exec_daemon.lock"
PID_FILE="/tmp/task_exec_daemon.pid"

acquire_lock() {
    exec 200>"$LOCK"
    flock -n 200 || { echo "已有实例运行 (PID=$(cat $PID_FILE 2>/dev/null))"; exit 1; }
    echo $$ > "$PID_FILE"
}

acquire_lock
echo "[daemon] 启动 PID=$$"

cleanup() {
    echo "[daemon] 收到退出信号"
    rm -f "$LOCK" "$PID_FILE"
    exit 0
}
trap cleanup SIGTERM SIGINT SIGHUP

while true; do
    python3 /home/admin/openclaw/workspace/scripts/task_executor.py
    EXIT=$?
    echo "[daemon] task_executor 退出码=$EXIT，3秒后重启"
    sleep 3
done
