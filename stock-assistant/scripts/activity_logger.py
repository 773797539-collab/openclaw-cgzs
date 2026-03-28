#!/usr/bin/env python3
"""
activity_logger.py - 从 git log 自动提取今日操作，追加到 tasks.json
只记录有实质内容的 commit，自动去重
"""
import json, subprocess, os
from datetime import datetime

WORKSPACE = "/home/admin/openclaw/workspace"
TASKS_FILE = f"{WORKSPACE}/portal/status/tasks.json"
GIT_LOG_CACHE = f"{WORKSPACE}/data/.activity_cache"

# 只记录这些前缀的 commit（实质性操作）
COMMIT_PREFIXES = (
    "fix", "feat", "add", "new", "build", "create",
    "implement", "setup", "config", "init", "上线",
    "修复", "新增", "搭建", "建立", "实现"
)

# 跳过这些关键词（琐碎维护）
SKIP_KEYWORDS = (
    "typo", "style:", "refactor:", "cleanup", "clean:", "lint",
    "Merge", "merge", "chore:", "docs:", "ci:"
)

def get_today_commits():
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", f"--since={today} 00:00", "--no-merges", "--all"],
            cwd=WORKSPACE, capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip().split('\n') if result.stdout.strip() else []
    except:
        return []

def load_tasks():
    if os.path.exists(TASKS_FILE):
        with open(TASKS_FILE) as f:
            return json.load(f)
    return {"doing": [], "todo": [], "done": [], "blocked": [], "lastUpdated": ""}

def save_tasks(tasks):
    tasks["lastUpdated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(TASKS_FILE, "w") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

def load_cache():
    if os.path.exists(GIT_LOG_CACHE):
        with open(GIT_LOG_CACHE) as f:
            return set(json.load(f))
    return set()

def save_cache(hashes):
    os.makedirs(os.path.dirname(GIT_LOG_CACHE), exist_ok=True)
    with open(GIT_LOG_CACHE, "w") as f:
        json.dump(list(hashes), f)

def is_meaningful(msg):
    """判断是否是有实质内容的 commit"""
    msg_lower = msg.lower()
    # 跳过琐碎的
    for kw in SKIP_KEYWORDS:
        if kw.lower() in msg_lower:
            return False
    # 必须以有意义的前缀开头
    return any(msg.startswith(p) for p in COMMIT_PREFIXES)

def commit_to_task(line):
    """把 git commit 信息转成任务格式"""
    parts = line.split(' ', 1)
    if len(parts) < 2:
        return None
    h, msg = parts[0], parts[1].strip()
    if not is_meaningful(msg):
        return None
    return {
        "name": msg,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "workers": "主控 Agent",
        "desc": f"Git: {h[:8]}",
        "result": "已完成",
        "type": "commit"
    }

def main():
    commits = get_today_commits()
    if not commits:
        return

    cache = load_cache()
    tasks = load_tasks()

    # 已有 commit hash 集合（用于去重）
    existing_hashes = set()
    for lst in [tasks.get("done",[]), tasks.get("todo",[]), tasks.get("doing",[])]:
        for t in lst:
            desc = t.get("desc","")
            if desc.startswith("Git: "):
                existing_hashes.add(desc[5:])

    new_count = 0
    for line in commits:
        h = line.split(' ', 1)[0] if ' ' in line else ''
        if h in cache or h in existing_hashes:
            continue
        task = commit_to_task(line)
        if task:
            tasks["done"].insert(0, task)
            new_count += 1
            cache.add(h)

    if new_count > 0:
        save_tasks(tasks)
        save_cache(cache)
        print(f"✅ 新增 {new_count} 条任务记录")
    else:
        print("无新任务")

if __name__ == "__main__":
    main()
