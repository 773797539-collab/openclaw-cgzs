#!/usr/bin/env python3
"""
portal_task_hook.py - 接收门户页发起的任务，生成任务文件到inbox
用法: python3 portal_task_hook.py "任务内容"
"""
import sys
import os
from datetime import datetime

INBOX_DIR = "/home/admin/openclaw/workspace/stock-assistant/tasks/inbox"
os.makedirs(INBOX_DIR, exist_ok=True)

def create_task(content):
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"TASK-MANUAL-{ts}.md"
    path = os.path.join(INBOX_DIR, filename)
    with open(path, "w") as f:
        f.write(f"# {content}\n\n")
        f.write(f"**创建时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**来源**: 门户页下发\n")
        f.write(f"**状态**: 等待处理\n\n")
        f.write(f"## 任务内容\n\n{content}\n\n")
        f.write(f"## 执行记录\n\n- 待执行\n")
    print(f"任务已创建: {filename}")
    return filename

if __name__ == "__main__":
    if len(sys.argv) > 1:
        content = " ".join(sys.argv[1:])
        create_task(content)
    else:
        print("用法: python3 portal_task_hook.py '任务内容'")
