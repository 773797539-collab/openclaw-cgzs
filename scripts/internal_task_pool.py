#!/usr/bin/env python3
"""
internal_task_pool.py - 内部任务池（无外部任务时执行）

Token > 0 时，每轮 heartbeat 从此池取任务执行。
任务池在 tasks/internal_pool.json 中维护。

每次 heartbeat：
1. 先检查 Token
2. 再检查内部任务池
3. 有任务就执行，无任务才静默
"""
import subprocess
import json
import os
import sys
from datetime import datetime
from pathlib import Path

WORKSPACE = "/home/admin/openclaw/workspace"
POOL_FILE = f"{WORKSPACE}/stock-assistant/tasks/internal_pool.json"
API_KEY = "sk-cp-B-h-RjQvCGBUCL42doqN1zKJMqhUx1McK-23ceE0nk7WAkHVzqby80U9S2TL6fjQUTolm7aobtX9squzXW5Vsoc-mUYK32RS9ohNwmruEg6vcfU0TjPjTi0"

TASK_DEFINITIONS = {
    "update_system_json": {
        "name": "更新 system.json",
        "script": f"python3 {WORKSPACE}/scripts/update-system-json.py",
        "desc": "更新门户 system.json（Token/任务池/cron状态）"
    },
    "update_portal_index": {
        "name": "重建 Portal 首页",
        "script": f"cd {WORKSPACE}/portal && python3 build_index.py",
        "desc": "重建 Portal index.html"
    },
    "git_status_check": {
        "name": "检查 Git 状态",
        "script": f"cd {WORKSPACE} && git status --short && git log --oneline -1",
        "desc": "检查工作区是否干净，有无未提交"
    },
    "clean_pycache": {
        "name": "清理 __pycache__",
        "script": f"find {WORKSPACE} -name '__pycache__' -type d -exec rm -rf {{}} + 2>/dev/null; find {WORKSPACE} -name '*.pyc' -delete 2>/dev/null; echo 'cleaned'",
        "desc": "清理所有 Python 缓存文件"
    },
    "verify_json_health": {
        "name": "验证 JSON 健康度",
        "script": f"python3 {WORKSPACE}/scripts/verify_json.py",
        "desc": "检查 stock-assistant/data/ 所有 JSON 是否有效"
    },
    "dispatcher_status": {
        "name": "检查 Dispatcher 状态",
        "script": f"python3 {WORKSPACE}/stock-assistant/scripts/dispatcher.py --status",
        "desc": "检查 dispatcher workflow_history 状态"
    },
    "process_pending_queue": {
        "name": "处理待分发队列",
        "script": f"python3 {WORKSPACE}/stock-assistant/scripts/queue_processor.py",
        "desc": "处理 pending_stock_main.json 中的积压任务"
    },
    "update_memory": {
        "name": "更新 MEMORY.md 时间戳",
        "script": f"cd {WORKSPACE} && git add MEMORY.md && git commit -m 'docs: MEMORY.md自动更新' || echo 'nothing_to_commit'",
        "desc": "将 MEMORY.md 当前时间戳更新并 commit"
    },
    "git_fetch_rebase": {
        "name": "Git fetch + rebase",
        "script": f"cd {WORKSPACE} && git stash && git fetch origin && git rebase origin/master && git stash pop || echo 'rebase_done'",
        "desc": "同步远程更改"
    },
    "verify_cron_jobs": {
        "name": "验证 Cron 任务注册",
        "script": f"openclaw cron list 2>/dev/null | grep -E 'market|morning|inbox|backup' || echo 'cron_check_done'",
        "desc": "检查 market_open/close、morning_briefing、inbox cron 是否注册"
    },
    "clean_workflow_history": {
        "name": "清理过期 workflow 历史",
        "script": f"python3 -c \"import json; d=json.load(open('{WORKSPACE}/portal/status/workflow_history.json')); stale=[w for w in d.get('workflows',[]) if w.get('status')=='completed' and 'WORKFLOW-2026-0326' in w.get('id','')]; print(f'清理{{len(stale)}}条过期workflow'); d['workflows']=[w for w in d.get('workflows',[]) if w not in stale]; open('{WORKSPACE}/portal/status/workflow_history.json','w').write(json.dumps(d,ensure_ascii=False,indent=2))\"",
        "desc": "删除 2026-03-26 的过期 workflow 记录（保留近期的）"
    },
    "daily_status_report": {
        "name": "daily_status 日报",
        "script": f"python3 {WORKSPACE}/scripts/daily_status.py >> {WORKSPACE}/stock-assistant/reports/daily-$(date +%Y-%m-%d).log 2>&1 && echo daily_report_ok",
        "desc": "运行 daily_status.py 写入日报 log"
    },
    "cron_health_run": {
        "name": "cron 健康检查运行",
        "script": f"timeout 30 python3 {WORKSPACE}/stock-assistant/scripts/cron_health_check.py 2>&1 | head -30",
        "desc": "实际运行 cron 健康检查"
    },
    "diag_system": {
        "name": "全系统诊断",
        "script": f"python3 {WORKSPACE}/stock-assistant/scripts/diag.py 2>&1 | tail -30",
        "desc": "运行 diag.py 全系统诊断"
    },
    "git_commits_summary": {
        "name": "当日 Git 提交汇总",
        "script": f"cd {WORKSPACE} && git log --oneline --since='8 hours ago' | head -20",
        "desc": "汇总当日 git commits"
    },
    "portal_rebuild": {
        "name": "Portal 重建",
        "script": f"cd {WORKSPACE}/portal && python3 build_index.py && echo portal_rebuilt",
        "desc": "重建 Portal 首页"
    }
}

def get_pool():
    if os.path.exists(POOL_FILE):
        with open(POOL_FILE) as f:
            return json.load(f)
    # 初始化
    pool = []
    for task_id, info in TASK_DEFINITIONS.items():
        pool.append({
            "id": task_id,
            "name": info["name"],
            "desc": info["desc"],
            "lastRun": None,
            "runCount": 0,
            "status": "pending"
        })
    return pool

def save_pool(pool):
    with open(POOL_FILE, "w") as f:
        json.dump(pool, f, ensure_ascii=False, indent=2)

def run_task(task_id):
    info = TASK_DEFINITIONS[task_id]
    print(f"[Internal Task] 执行: {info['name']} - {info['desc']}", flush=True)
    try:
        result = subprocess.run(
            info["script"],
            shell=True, capture_output=True, text=True, timeout=60
        )
        output = result.stdout.strip()[:200]
        print(f"[Internal Task] 结果: {output}", flush=True)
        return result.returncode == 0
    except Exception as e:
        print(f"[Internal Task] 失败: {e}", flush=True)
        return False

def get_token_status():
    try:
        result = subprocess.run([
            "curl", "-s",
            "https://www.minimaxi.com/v1/api/openplatform/coding_plan/remains",
            "-H", f"Authorization: Bearer {API_KEY}",
            "-H", "Content-Type: application/json"
        ], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout)
        for m in data.get("model_remains", []):
            if "MiniMax-M*" in m.get("model_name", ""):
                return m["current_interval_usage_count"], m["current_interval_total_count"]
        return None
    except:
        return None

def process_one_task():
    """取队列中第一个 pending 任务执行"""
    pool = get_pool()
    for task in pool:
        if task["status"] == "pending":
            ok = run_task(task["id"])
            task["lastRun"] = datetime.now().isoformat()
            task["runCount"] += 1
            if ok:
                task["status"] = "done"
            else:
                task["status"] = "failed"
            save_pool(pool)
            return task["name"], ok
    return None, None

def show_status():
    pool = get_pool()
    pending = [t for t in pool if t["status"] == "pending"]
    done = [t for t in pool if t["status"] == "done"]
    failed = [t for t in pool if t["status"] == "failed"]
    token = get_token_status()
    if token:
        remaining, total = token
        pct = remaining / total * 100
        print(f"Token: {remaining}/{total} ({pct:.1f}%)")
    else:
        print("Token: API失败")
    print(f"任务池: {len(pending)} 待执行, {len(done)} 已完成, {len(failed)} 失败")
    if pending:
        print(f"下一个: {pending[0]['name']}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--status":
        show_status()
    else:
        name, ok = process_one_task()
        if name:
            print(f"✅ 已执行: {name}" if ok else f"❌ 失败: {name}")
        else:
            print("队列空，无任务执行")
