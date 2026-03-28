#!/usr/bin/env python3
"""备份脚本 - 每日03:00自动执行
备份内容: Git仓库打包、portal状态、inbox任务
"""
import subprocess, json, os, shutil
from datetime import datetime

BACKUP_DIR = "/home/admin/openclaw/workspace/backups"
os.makedirs(BACKUP_DIR, exist_ok=True)

ts = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_file = f"{BACKUP_DIR}/openclaw_backup_{ts}.tar.gz"

# 打包workspace（排除.git/objects/pack）
result = subprocess.run(
    ["tar", "-czf", backup_file,
     "--exclude=.git/objects/pack",
     "--exclude=.git/refs/stash",
     "-C", "/home/admin/openclaw", "workspace"],
    capture_output=True, text=True
)
if result.returncode == 0:
    size = os.path.getsize(backup_file) / 1024 / 1024
    print(f"✅ Backup: {backup_file} ({size:.1f}MB)")
else:
    print(f"❌ Backup failed: {result.stderr}")
