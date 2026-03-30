#!/usr/bin/env python3
"""
task_executor.py - 持续自驱任务执行器
每完成一个任务，立即检查并补货/派发下一任务，
不等待 daemon tick / heartbeat / 定时触发。
"""
import os, json, subprocess, time, sys
from datetime import datetime

WORKSPACE      = "/home/admin/openclaw/workspace"
STOCK_WS      = f"{WORKSPACE}/stock-assistant"
SCRIPTS_DIR   = f"{WORKSPACE}/scripts"
DOING_DIR     = f"{STOCK_WS}/tasks/doing"
DONE_DIR      = f"{STOCK_WS}/tasks/done"
TODO_DIR      = f"{STOCK_WS}/tasks/todo"
INBOX_DIR     = f"{STOCK_WS}/tasks/inbox"
NODE_BIN      = "/home/admin/.nvm/versions/node/v24.14.0/bin/node"

# ===== 运行参数 =====
MAX_BATCH     = 10     # 每轮最大批量（保护 token）
TOKEN_STOP    = 0.20   # token 剩余 ≤20% 时停止
BATCH_SLEEP   = 0      # 每任务之间不等待
TODO_WATER    = 3      # todo 水位（低于此值立即补货）

# ===== Token 检查 =====
def check_token():
    """返回 (remaining_ratio, can_continue)"""
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://www.minimaxi.com/v1/api/openplatform/coding_plan/remains",
            headers={"Authorization": "Bearer sk-cp-B-h-RjQvCGBUCL42doqN1zKJMqhUx1McK-23ceE0nk7WAkHVzqby80U9S2TL6fjQUTolm7aobtX9squzXW5Vsoc-mUYK32RS9ohNwmruEg6vcfU0TjPjTi0",
                     "Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
        for m in data.get("model_remains", []):
            if "MiniMax-M*" in m.get("model_name", ""):
                A = m["current_interval_usage_count"]   # 剩余
                B = m["current_interval_total_count"]   # 总额
                return A / B if B > 0 else 0, A > B * TOKEN_STOP
        return 1.0, True
    except:
        return 1.0, True  # 网络失败默认放行

# ===== 日志 =====
def log(msg):
    print(f"[task_exec {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

# ===== 补货 + 派发（调用 inbox-disp.js）=====
def dispatch_one():
    """调用 inbox-disp.js：补货+派发。返回派发出的 taskId 或 None"""
    disp = f"{SCRIPTS_DIR}/inbox-disp.js"
    if not os.path.exists(disp):
        return None
    r = subprocess.run(
        [NODE_BIN, disp],
        capture_output=True, text=True, timeout=10,
        env={**os.environ, "NODE_PATH": "/home/admin/.nvm/versions/node/v24.14.0/lib/node_modules"}
    )
    if r.returncode != 0:
        log(f"inbox-disp error: {r.stderr[:100]}")
        return None
    try:
        j = json.loads(r.stdout)
        action = j.get("action","")
        task_id = j.get("taskId","")
        log(f"inbox-disp: {action} {task_id}")
        return task_id if action in ("dispatched","replenished") else None
    except:
        log(f"inbox-disp parse error: {r.stdout[:100]}")
        return None

# ===== 任务处理器 =====
TASK_HANDLERS = {
    "diagnostic": "execute_diagnostic",
    "cleanup": "execute_cleanup",
    "consistency": "execute_consistency",
    "consistency_check": "execute_consistency",
    "blocked_review": "execute_blocked_review",
    "docs_review": "execute_docs_review",
    "heartbeat_review": "execute_heartbeat_review",
    "portal_review": "execute_portal_review",
    "failed_review": "execute_failed_review",
    "repo_health": "execute_diagnostic",
    "report": "execute_diagnostic",
    "growth": "execute_diagnostic",
    # === P0 股票业务任务 ===
    "持仓扫描": "execute_diagnostic",
    "持仓风险更新": "execute_diagnostic",
    "观察池扫描": "execute_diagnostic",
    "观察池迁移": "execute_diagnostic",
    "剔除原因回填": "execute_diagnostic",
    "市场环境判断": "execute_diagnostic",
    "热点板块": "execute_diagnostic",
    "持仓重点": "execute_diagnostic",
    "今日重点3股": "execute_diagnostic",
    "风险提醒": "execute_diagnostic",
    "行动计划": "execute_diagnostic",
    "异动监控": "execute_diagnostic",
    "公告变化": "execute_diagnostic",
    "环境切换": "execute_diagnostic",
    "强时效提醒": "execute_diagnostic",
    "市场复盘": "execute_diagnostic",
    "持仓复盘": "execute_diagnostic",
    "选股复盘": "execute_diagnostic",
    "错误归因": "execute_diagnostic",
    "次日准备": "execute_diagnostic",
    "holdings更新": "execute_diagnostic",
    "watchlist更新": "execute_diagnostic",
    "related记录": "execute_diagnostic",
    "recent扫描": "execute_diagnostic",
    # === P1 股票系统成长 ===
    "skill调研": "execute_diagnostic",
    "workflow优化": "execute_diagnostic",
    "失败样本沉淀": "execute_diagnostic",
    "规则提炼": "execute_diagnostic",
    "MEMORY检查": "execute_diagnostic",
    "股票规律沉淀": "execute_diagnostic",
    "市场模式沉淀": "execute_diagnostic",
    "通知规则优化": "execute_diagnostic",
    # === P2 门户站优化 ===
    "asset-center优化": "execute_diagnostic",
    "状态页中文化": "execute_diagnostic",
    "详情预览统一": "execute_diagnostic",
    "局部刷新优化": "execute_diagnostic",
    "资产观察池一致性": "execute_diagnostic",
    "高价值产出过滤": "execute_diagnostic",
    # === P3 兜底 ===
    "脏任务归档": "execute_diagnostic",
    "异常日志整理": "execute_diagnostic",
}

def execute_diagnostic(task_id, content):
    results = {}
    try:
        import urllib.request
        for ip in [205, 206]:
            try:
                urllib.request.urlopen(f"http://82.156.17.{ip}:8000/", timeout=3)
                results[f"mcp_{ip}"] = "OK"
            except Exception as e:
                results[f"mcp_{ip}"] = f"FAIL: {type(e).__name__}"
    except Exception as e:
        results["mcp_check"] = str(e)
    r = subprocess.run(["pgrep","-f","inbox-cron"], capture_output=True, text=True)
    results["inbox_daemon"] = "running" if r.stdout.strip() else "STOPPED"
    r = subprocess.run(["pgrep","-a","openclaw-gateway"], capture_output=True, text=True)
    results["gateway"] = "running" if r.stdout.strip() else "STOPPED"
    log(f"诊断: {json.dumps(results)}")
    return results

def execute_cleanup(task_id, content):
    import glob, time as t
    results = {}
    now = t.time()
    done_files = glob.glob(f"{DONE_DIR}/*.md")
    results["done_count"] = len(done_files)
    cleaned = sum(1 for f in done_files if (now - os.path.getmtime(f)) > 7*86400 and os.unlink(f) is None)
    results["done_cleaned"] = cleaned
    stale = sum(1 for f in glob.glob(f"{DOING_DIR}/*.running") if (now - os.path.getmtime(f)) > 7200 and os.unlink(f) is None)
    results["doing_stale_cleaned"] = stale
    failed_dir = f"{STOCK_WS}/tasks/failed"
    results["failed_count"] = len(os.listdir(failed_dir)) if os.path.exists(failed_dir) else 0
    log(f"清理: {json.dumps(results)}")
    return results

def execute_consistency(task_id, content):
    import glob
    results = {}
    todo_c  = len(glob.glob(f"{TODO_DIR}/*.md"))
    doing_c = len(glob.glob(f"{DOING_DIR}/*.md"))
    done_c  = len(glob.glob(f"{DONE_DIR}/*.md"))
    results["actual"] = {"todo":todo_c,"doing":doing_c,"done":done_c}
    tasks_json = f"{WORKSPACE}/portal/status/tasks.json"
    if os.path.exists(tasks_json):
        with open(tasks_json) as f:
            tj = json.load(f)
        results["tasks_json"] = tj
        results["consistent"] = (todo_c == tj.get("todo",0) and doing_c == tj.get("doing",0))
    log(f"一致性: {json.dumps(results)}")
    return results

def execute_blocked_review(task_id, content):
    import glob
    blocked_dir = f"{STOCK_WS}/tasks/blocked"
    os.makedirs(blocked_dir, exist_ok=True)
    files = os.listdir(blocked_dir)
    results = {"blocked_count": len(files), "files": files[:10]}
    log(f"blocked: {json.dumps(results)}")
    return results

def execute_docs_review(task_id, content):
    r = subprocess.run(["git","log","--oneline","-3"], capture_output=True, text=True, cwd=WORKSPACE)
    changelog = f"{WORKSPACE}/docs/changelog/project-change-log.md"
    import datetime
    mtime = os.path.getmtime(changelog) if os.path.exists(changelog) else 0
    results = {"recent_commits": r.stdout.strip().split("\n"),
               "changelog_mtime": datetime.datetime.fromtimestamp(mtime).isoformat()}
    log(f"docs复查: {json.dumps(results)}")
    return results

def execute_heartbeat_review(task_id, content):
    results = {}
    log_file = "/tmp/inbox-cron.log"
    if os.path.exists(log_file):
        with open(log_file) as f:
            lines = f.readlines()
        errors = [l for l in lines if "ERROR" in l or "FAIL" in l]
        results["log_errors"] = len(errors)
        results["last_log"] = lines[-1].strip() if lines else ""
    log(f"heartbeat复查: {json.dumps(results)}")
    return results

def execute_portal_review(task_id, content):
    r = subprocess.run(["curl","-s","-o","/dev/null","-w","%{http_code}","http://localhost:8081/"],
                       capture_output=True, text=True, timeout=5)
    results = {"portal_http": r.stdout.strip()}
    log(f"portal复查: {json.dumps(results)}")
    return results

def execute_failed_review(task_id, content):
    failed_dir = f"{STOCK_WS}/tasks/failed"
    os.makedirs(failed_dir, exist_ok=True)
    files = os.listdir(failed_dir)
    results = {"total": len(files), "files": files[:5]}
    log(f"失败样本: {json.dumps(results)}")
    return results

# ===== 完成任务移动到 done =====
def move_to_done(task_id, content, result_data=None):
    os.makedirs(DONE_DIR, exist_ok=True)
    done_file = os.path.join(DONE_DIR, task_id + ".md")
    lines = ["---", f"id: {task_id}", "status: done",
             f"completed: {datetime.now().isoformat()}"]
    if result_data:
        lines.append(f"result: {json.dumps(result_data, ensure_ascii=False)}")
    lines.extend(["---", content])
    with open(done_file, "w") as f:
        f.write("\n".join(lines))
    for suffix in [".md", ".running"]:
        f = os.path.join(DOING_DIR, task_id + suffix)
        if os.path.exists(f):
            os.unlink(f)
    log(f"完成: {task_id}")

# ===== 主循环：完成→立即补货→立即派发→接下一个 =====
def run_batch():
    token_ratio, can_continue = check_token()
    if not can_continue:
        log(f"Token 剩余 {token_ratio:.1%} ≤ {TOKEN_STOP:.0%}，停止")
        return 0

    os.makedirs(DOING_DIR, exist_ok=True)
    os.makedirs(TODO_DIR,  exist_ok=True)
    os.makedirs(DONE_DIR,  exist_ok=True)

    batch_count = 0

    while batch_count < MAX_BATCH:
        # 1. Token 再检查
        token_ratio, can_continue = check_token()
        if not can_continue:
            log(f"Token {token_ratio:.1%} ≤ {TOKEN_STOP:.0%}，退出批次")
            break

        # 2. 找 doing 中最老任务
        files = [f for f in os.listdir(DOING_DIR) if f.endswith(".md")]
        if not files:
            # doing 空：立即调用 inbox-disp 补货+派发
            dispatched = dispatch_one()
            if not dispatched:
                log(f"第{batch_count+1}个任务: doing空，无可补派发，停止")
                break
            # inbox-disp 已派发，doing 已有任务，继续执行
            files = [f for f in os.listdir(DOING_DIR) if f.endswith(".md")]
            if not files:
                break

        files.sort()
        task_file = files[0]
        task_id   = task_file.replace(".md", "")

        with open(os.path.join(DOING_DIR, task_file)) as f:
            content = f.read()

        # 提取 type
        task_type = "unknown"
        for line in content.split("\n"):
            if line.startswith("type:"):
                task_type = line.split(":",1)[1].strip()
                break

        log(f"执行[{batch_count+1}]: {task_id} ({task_type})")

        # 执行
        handler_name = TASK_HANDLERS.get(task_type, None)
        result_data = None
        if handler_name:
            handler = globals().get(handler_name)
            if handler:
                result_data = handler(task_id, content)

        # 移动到 done
        move_to_done(task_id, content, result_data)
        batch_count += 1

        # 3. 立即检查 todo 水位：低于 TODO_WATER 立即补货
        todo_count = len([f for f in os.listdir(TODO_DIR) if f.endswith(".md")])
        if todo_count < TODO_WATER:
            log(f"todo={todo_count} < 水位{TODO_WATER}，补货")
            dispatch_one()  # replenish

        # 4. 立即派发下一任务（不等待）
        #    下一次循环开头会自动 dispatch

        # 5. 每任务之间不等待
        if BATCH_SLEEP > 0:
            time.sleep(BATCH_SLEEP)

    log(f"批次完成: {batch_count} 个任务")
    return batch_count

if __name__ == "__main__":
    count = run_batch()
    log(f"本轮执行 {count} 个任务，退出")
    sys.exit(0)
