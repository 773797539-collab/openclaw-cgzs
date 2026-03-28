#!/bin/bash
# run_queue_processor.sh - 被 inbox-to-stock-main cron 调用
# 每5分钟执行一次，读取pending队列并派发
python3 /home/admin/openclaw/workspace/stock-assistant/scripts/queue_processor.py >> /home/admin/openclaw/workspace/logs/queue_processor.log 2>&1
