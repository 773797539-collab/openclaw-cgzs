#!/usr/bin/env python3
"""
task_executor.py - 真实任务执行器
从 tasks/doing/ 读取任务，执行之，将结果写入 tasks/done/

每次运行执行 1 个任务。
HEARTBEAT 调用方式: python3 scripts/task_executor.py
"""
import os, json, subprocess, time
from datetime import datetime

WORKSPACE = "/home/admin/openclaw/workspace"
DOING_DIR = f"{WORKSPACE}/stock-assistant/tasks/doing"
DONE_DIR  = f"{WORKSPACE}/stock-assistant/tasks/done"
LOG_DIR   = f"{WORKSPACE}/logs"

TASK_HANDLERS = {
    "diagnostic": "execute_diagnostic",
    "cleanup": "execute_cleanup",
    "consistency_check": "execute_consistency_check",
    "blocked_review": "execute_blocked_review",
    "docs_review": "execute_docs_review",
    "heartbeat_review": "execute_heartbeat_review",
    "portal_review": "execute_portal_review",
    "failed_review": "execute_failed_review",
    "repo_health": "execute_diagnostic",  # 复用
    "report": "execute_diagnostic",
    "growth": "execute_diagnostic",
}

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[task_exec {ts}] {msg}", flush=True)

def move_to_done(task_id, content, result_data=None):
    os.makedirs(DONE_DIR, exist_ok=True)
    done_file = os.path.join(DONE_DIR, task_id + ".md")
    lines = [
        "---",
        f"id: {task_id}",
        f"status: done",
        f"completed: {datetime.now().isoformat()}",
    ]
    if result_data:
        lines.append(f"result: {json.dumps(result_data, ensure_ascii=False)}")
    lines.extend(["---", content])
    with open(done_file, "w") as f:
        f.write("\n".join(lines))
    # 删除源文件（.md 和 .running）
    for suffix in [".md", ".running"]:
        f = os.path.join(DOING_DIR, task_id + suffix)
        if os.path.exists(f):
            os.unlink(f)
    log(f"完成: {task_id}")

def execute_diagnostic(task_id, content):
    results = {}
    # 1. MCP 连通性检查
    try:
        import urllib.request
        for ip in [205, 206]:
            try:
                r = urllib.request.urlopen(f"http://82.156.17.{ip}:8000/", timeout=3)
                results[f"mcp_{ip}"] = "OK"
            except Exception as e:
                results[f"mcp_{ip}"] = f"FAIL: {type(e).__name__}"
    except Exception as e:
        results["mcp_check"] = str(e)

    # 2. inbox-cron daemon 检查
    r = subprocess.run(["pgrep", "-f", "inbox-cron"], capture_output=True, text=True)
    results["inbox_daemon"] = "running" if r.stdout.strip() else "STOPPED"

    # 3. cron daemon 检查
    r = subprocess.run(["ps", "aux"], capture_output=True, text=True)
    results["cron_daemon"] = "running" if "cron" in r.stdout and "grep" not in r.stdout else "STOPPED"

    # 4. gateway 检查
    r = subprocess.run(["pgrep", "-a", "openclaw-gateway"], capture_output=True, text=True)
    results["gateway"] = "running" if r.stdout.strip() else "STOPPED"

    log(f"诊断结果: {json.dumps(results)}")
    return results

def execute_cleanup(task_id, content):
    results = {}
    import glob

    # 1. 统计 done 文件数
    done_files = glob.glob(f"{DONE_DIR}/*.md")
    results["done_count"] = len(done_files)

    # 2. 清理 done/ 下超过7天的文件
    import time
    now = time.time()
    cleaned = 0
    for f in done_files:
        mtime = os.path.getmtime(f)
        age_days = (now - mtime) / 86400
        if age_days > 7:
            os.unlink(f)
            cleaned += 1
    results["done_cleaned"] = cleaned

    # 3. 清理 doing/ 下超过2小时的 .running 文件
    doing_runnings = glob.glob(f"{DOING_DIR}/*.running")
    stale = 0
    for f in doing_runnings:
        mtime = os.path.getmtime(f)
        age_hours = (now - mtime) / 3600
        if age_hours > 2:
            os.unlink(f)
            stale += 1
    results["doing_stale_cleaned"] = stale

    # 4. failed 目录检查
    failed_dir = f"{WORKSPACE}/stock-assistant/tasks/failed"
    if os.path.exists(failed_dir):
        failed_files = os.listdir(failed_dir)
        results["failed_count"] = len(failed_files)
    else:
        results["failed_count"] = 0

    log(f"清理结果: {json.dumps(results)}")
    return results

def execute_consistency_check(task_id, content):
    results = {}
    import glob

    # 对比 tasks/ 目录文件数 vs tasks.json
    todo_count = len(glob.glob(f"{WORKSPACE}/stock-assistant/tasks/todo/*.md"))
    doing_count = len(glob.glob(f"{WORKSPACE}/stock-assistant/tasks/doing/*.md"))
    done_count = len(glob.glob(f"{WORKSPACE}/stock-assistant/tasks/done/*.md"))

    tasks_json = f"{WORKSPACE}/portal/status/tasks.json"
    if os.path.exists(tasks_json):
        with open(tasks_json) as f:
            tj = json.load(f)
        results["tasks_json"] = tj
        results["diff_todo"] = todo_count - tj.get("todo", 0)
        results["diff_doing"] = doing_count - tj.get("doing", 0)
        results["diff_done"] = done_count - tj.get("done", 0)
        results["consistent"] = (results["diff_todo"] == 0 and results["diff_doing"] == 0)

    results["actual"] = {"todo": todo_count, "doing": doing_count, "done": done_count}
    log(f"一致性检查: {json.dumps(results)}")
    return results

def execute_blocked_review(task_id, content):
    results = {}
    blocked_dir = f"{WORKSPACE}/stock-assistant/tasks/blocked"
    os.makedirs(blocked_dir, exist_ok=True)
    blocked_files = [f for f in os.listdir(blocked_dir) if f.endswith(".md")]
    results["blocked_count"] = len(blocked_files)
    results["files"] = blocked_files[:10]  # 最多10个
    log(f"blocked复查: {json.dumps(results)}")
    return results

def execute_docs_review(task_id, content):
    results = {}
    import subprocess

    # 检查 git log 是否与 changelog 一致
    r = subprocess.run(["git", "log", "--oneline", "-3"], capture_output=True, text=True, cwd=WORKSPACE)
    results["recent_commits"] = r.stdout.strip().split("\n")

    # 检查 docs/changelog 最后修改时间
    changelog = f"{WORKSPACE}/docs/changelog/project-change-log.md"
    if os.path.exists(changelog):
        mtime = os.path.getmtime(changelog)
        import datetime
        results["changelog_mtime"] = datetime.datetime.fromtimestamp(mtime).isoformat()

    log(f"docs复查: {json.dumps(results)}")
    return results

def execute_heartbeat_review(task_id, content):
    results = {}
    import subprocess

    # 检查 inbox-cron.log 是否有错误
    log_file = "/tmp/inbox-cron.log"
    if os.path.exists(log_file):
        with open(log_file) as f:
            lines = f.readlines()
        results["log_lines"] = len(lines)
        errors = [l for l in lines if "ERROR" in l or "FAIL" in l]
        results["log_errors"] = len(errors)
        results["last_log"] = lines[-1].strip() if lines else ""
    else:
        results["log_file"] = "NOT_FOUND"

    # cron daemon
    r = subprocess.run(["ps", "aux"], capture_output=True, text=True)
    results["cron_daemon"] = "OK" if "cron" in r.stdout else "MISSING"

    log(f"heartbeat复查: {json.dumps(results)}")
    return results

def execute_portal_review(task_id, content):
    results = {}
    import subprocess, glob

    # portal 可访问性
    r = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://localhost:8081/"],
                       capture_output=True, text=True, timeout=5)
    results["portal_http"] = r.stdout.strip()

    # tasks.json vs actual
    todo_count = len(glob.glob(f"{WORKSPACE}/stock-assistant/tasks/todo/*.md"))
    doing_count = len(glob.glob(f"{WORKSPACE}/stock-assistant/tasks/doing/*.md"))
    done_count  = len(glob.glob(f"{WORKSPACE}/stock-assistant/tasks/done/*.md"))
    results["actual"] = {"todo": todo_count, "doing": doing_count, "done": done_count}

    log(f"portal复查: {json.dumps(results)}")
    return results

def execute_failed_review(task_id, content):
    results = {}
    import glob
    failed_dir = f"{WORKSPACE}/stock-assistant/tasks/failed"
    os.makedirs(failed_dir, exist_ok=True)
    failed_files = os.listdir(failed_dir)
    results["total"] = len(failed_files)
    results["files"] = failed_files[:5]
    log(f"失败样本整理: {json.dumps(results)}")
    return results

def main():
    # 找最早的任务文件（.md 且有对应的 .running）
    if not os.path.exists(DOING_DIR):
        log("doing目录不存在")
        return

    files = [f for f in os.listdir(DOING_DIR) if f.endswith(".md")]
    if not files:
        log("doing空，无任务执行")
        return

    # 按文件名排序（时间戳在文件名里）
    files.sort()
    task_file = files[0]
    task_id = task_file.replace(".md", "")

    with open(os.path.join(DOING_DIR, task_file)) as f:
        content = f.read()

    # 提取类型
    task_type = "unknown"
    for line in content.split("\n"):
        if line.startswith("type:"):
            task_type = line.split(":", 1)[1].strip()
            break

    log(f"执行: {task_id} ({task_type})")

    # 找处理器
    handler_name = TASK_HANDLERS.get(task_type, None)
    result_data = None

    if handler_name:
        handler = globals().get(handler_name)
        if handler:
            result_data = handler(task_id, content)
        else:
            log(f"处理器 {handler_name} 未找到")
    else:
        log(f"未知任务类型: {task_type}")

    # 移动到 done
    move_to_done(task_id, content, result_data)

if __name__ == "__main__":
    main()
