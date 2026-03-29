#!/bin/bash
# scripts/diag.sh - 轻量系统自检脚本
# 快速检查：gateway / cron / inbox 积压 / tasks.json / disk

GATEWAY_OK=$(systemctl --user is-active openclaw-gateway 2>/dev/null | grep -c "active")
CRON_PID=$(pgrep -a cron 2>/dev/null | grep -v grep | grep -c "cron")
INBOX_COUNT=$(ls /home/admin/openclaw/workspace/stock-assistant/tasks/inbox/*.md 2>/dev/null | wc -l)
TASKS_FILE="/home/admin/openclaw/workspace/portal/status/tasks.json"
DISK_USAGE=$(df -h /home/admin/openclaw/workspace | awk 'NR==2 {print $5}')

GW_UPTIME=""
if [ -n "$(pgrep -f 'openclaw-gateway')" ]; then
    GW_PID=$(pgrep -f 'openclaw-gateway' | head -1)
    GW_UPTIME=$(ps -p $GW_PID -o etime= 2>/dev/null | tr -d ' ')
fi

echo "=== 系统自检 $(date '+%Y-%m-%d %H:%M:%S') ==="
echo "gateway : $GATEWAY_OK (1=active) | uptime: $GW_UPTIME"
echo "cron    : $CRON_PID (>=1=running)"
echo "inbox   : $INBOX_COUNT 待处理"
echo "disk    : $DISK_USAGE 使用"
if [ -f "$TASKS_FILE" ]; then
    LAST=$(python3 -c "import json; print(json.load(open('$TASKS_FILE')).get('lastUpdated','N/A'))" 2>/dev/null)
    echo "snapshot : lastUpdated=$LAST"
fi
echo "==========================="

# 异常标记
[ "$GATEWAY_OK" != "1" ] && echo "[WARN] gateway not active"
[ "$INBOX_COUNT" -gt 5 ] && echo "[WARN] inbox 积压 > 5"
[ "$CRON_PID" -lt 1 ] && echo "[WARN] cron daemon not running"
