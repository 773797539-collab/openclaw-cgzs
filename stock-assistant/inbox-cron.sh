#!/bin/bash
# inbox-cron.sh - Linux系统cron调用入口（非OpenClaw cron）
# 职责：每5分钟执行process_inbox.py
# 特点：PID锁防止并发 + 绝对路径 + stdout/stderr重定向到log
# OpenClaw inbox cron已禁用（agent活跃时systemEvent无法送达）

LOCKFILE="/tmp/inbox-cron.lock"
PIDFILE="/tmp/inbox-cron.pid"

# PID锁：防止上一个cron还没跑完下一个又触发
if [ -f "$PIDFILE" ]; then
    OLD=$(cat $PIDFILE)
    if [ -d "/proc/$OLD" ]; then exit 0; fi
fi
echo $$ > $PIDFILE

# 重定向stdout/stderr到log
exec >> /tmp/inbox-cron.log 2>&1
echo "$(date '+%Y-%m-%d %H:%M:%S') [$$] inbox-cron start"

# 执行入口脚本
cd /home/admin/openclaw/workspace/stock-assistant
/usr/bin/python3 scripts/process_inbox.py

echo "$(date '+%Y-%m-%d %H:%M:%S') [$$] inbox-cron done"
rm -f $PIDFILE
