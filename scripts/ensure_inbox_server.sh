#!/bin/bash
# 检查并启动 portal inbox server
pgrep -f 'portal_inbox_server.py' > /dev/null ||   nohup python3 /home/admin/openclaw/workspace/scripts/portal_inbox_server.py > /dev/null 2>&1 &

