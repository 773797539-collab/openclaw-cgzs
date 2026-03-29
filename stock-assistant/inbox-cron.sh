#!/bin/bash
LOCKFILE="/tmp/inbox-cron.lock"
PIDFILE="/tmp/inbox-cron.pid"
if [ -f "$PIDFILE" ]; then
    OLD=$(cat $PIDFILE)
    if [ -d "/proc/$OLD" ]; then exit 0; fi
fi
echo $$ > $PIDFILE
exec >> /tmp/inbox-cron.log 2>&1
echo "$(date '+%Y-%m-%d %H:%M:%S') [$$] inbox-cron start"
cd /home/admin/openclaw/workspace/stock-assistant
/usr/bin/python3 scripts/process_inbox.py
echo "$(date '+%Y-%m-%d %H:%M:%S') [$$] inbox-cron done"
rm -f $PIDFILE
