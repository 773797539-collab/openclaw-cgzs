#!/bin/bash
# bootstrap.sh - 容器重启后自拉起脚本
# 用法: bash bootstrap.sh
# 或 @reboot /bin/bash /home/admin/openclaw/workspace/scripts/bootstrap.sh

set -u

LOGFILE="/tmp/bootstrap.log"
WORKSPACE="/home/admin/openclaw/workspace"
STOCK_WS="$WORKSPACE/stock-assistant"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [$$] $*" >> "$LOGFILE"
}

start_if_dead() {
    local name="$1"
    local cmd="$2"
    local pidfile="${3:-}"
    if [ -n "$pidfile" ] && [ -f "$pidfile" ] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then
        log "$name already running (pid=$(cat $pidfile))"
        return 1
    fi
    if pgrep -f "$cmd" > /dev/null 2>&1; then
        log "$name already running"
        return 1
    fi
    log "starting $name: $cmd"
    nohup bash -c "$cmd" >> "$LOGFILE" 2>&1 &
    [ -n "$pidfile" ] && echo $! > "$pidfile"
    return 0
}

log "=== bootstrap start ==="
log "host=$(cat /etc/hostname) container=$(cat /sys/class/dmi/id/chassis_type 2>/dev/null || echo unknown)"

# 1. inbox-cron daemon
start_if_dead "inbox-cron" \
    "while true; do cd $STOCK_WS && bash inbox-cron.sh; sleep 30; done" \
    "/tmp/inbox-cron-bootstrap.pid"

# 2. task-executor daemon
start_if_dead "task-executor" \
    "while true; do python3 $WORKSPACE/scripts/task_executor.py; sleep 10; done" \
    "/tmp/task-executor-bootstrap.pid"

# 3. openclaw-gateway
if ! pgrep -f "openclaw gateway" > /dev/null 2>&1; then
    log "starting openclaw-gateway"
    cd $WORKSPACE && nohup openclaw gateway start >> "$LOGFILE" 2>&1 &
else
    log "openclaw-gateway already running"
fi

# 4. portal (if directory exists)
if [ -d "$WORKSPACE/portal" ]; then
    if ! pgrep -f "python3.*portal/server" > /dev/null 2>&1; then
        log "starting portal"
        cd $WORKSPACE/portal && nohup python3 server.py >> "$LOGFILE" 2>&1 &
    else
        log "portal already running"
    fi
fi

sleep 3
log "=== bootstrap complete ==="
log "running processes:"
pgrep -f "inbox-cron|task_executor|openclaw.*gateway|portal/server" 2>/dev/null | while read pid; do
    log "  pid=$pid cmd=$(cat /proc/$pid/cmdline 2>/dev/null | tr '\0' ' ' | cut -d' ' -f2-)"
done
