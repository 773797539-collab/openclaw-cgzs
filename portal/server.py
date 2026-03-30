#!/usr/bin/env python3
"""
OpenClaw Agent Dashboard Portal Server - 主可观测中心
Serves JSON status endpoints and the main portal HTML page.
"""

import json
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse

# Configuration
PORT = 8081
STATUS_DIR = Path(__file__).parent / "status"
TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"
WORKSPACE = Path("/home/admin/openclaw/workspace")
MEMORY_DIR = WORKSPACE / "memory"
CHANGELOG_DIR = WORKSPACE / "docs" / "changelog"
BACKUPS_DIR = WORKSPACE / "backups"

app = FastAPI(title="OpenClaw Portal - 主可观测中心", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def read_json(filename: str):
    filepath = STATUS_DIR / filename
    if filepath.exists():
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


# ===== holdings / watchlist 数据读写（stock-assistant/data/）=====
DATA_DIR = Path("/home/admin/openclaw/workspace/stock-assistant/data")

def read_data_json(filename: str):
    fp = DATA_DIR / filename
    if fp.exists():
        with open(fp, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def write_data_json(filename: str, data):
    fp = DATA_DIR / filename
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return fp


def read_changelog_summary():
    changes = []
    changelog_file = CHANGELOG_DIR / "project-change-log.md"
    if changelog_file.exists():
        content = changelog_file.read_text(encoding="utf-8")
        entries = re.split(r'\n(?=## \d{4}-\d{2}-\d{2} )', content)
        for entry in entries[1:6]:
            lines = entry.strip().split('\n')
            date_line = lines[0].replace('## ', '').strip() if lines else ''
            summary_lines = []
            for line in lines[1:]:
                if line.startswith('### ') or line.startswith('## '):
                    break
                if line.startswith('**改动目标**'):
                    val = re.sub(r'\*\*[^*]+\*\*: ', '', line).strip()
                    if val:
                        summary_lines.append(val)
            changes.append({
                "date": date_line,
                "target": summary_lines[0] if summary_lines else date_line,
                "summary": '；'.join(summary_lines[:3]) if summary_lines else date_line
            })
    return changes[:5]


def read_memory_health():
    mem_files = sorted(MEMORY_DIR.glob("*.md")) if MEMORY_DIR.exists() else []
    total_size = 0
    latest_update = None
    file_list = []
    for f in mem_files:
        stat = f.stat()
        total_size += stat.st_size
        mtime = datetime.fromtimestamp(stat.st_mtime)
        file_list.append({"name": f.name, "size_kb": round(stat.st_size / 1024, 1), "updated": mtime.strftime("%Y-%m-%d %H:%M")})
        if latest_update is None or mtime > latest_update:
            latest_update = mtime

    score = 100
    if len(mem_files) < 3: score -= 30
    if total_size < 1000: score -= 20
    age_days = (datetime.now() - latest_update).days if latest_update else 999
    if age_days > 2: score -= 25
    elif age_days > 1: score -= 10

    if score >= 80: status, color = "优秀", "green"
    elif score >= 60: status, color = "良好", "yellow"
    elif score >= 40: status, color = "一般", "orange"
    else: status, color = "需关注", "red"

    return {
        "total_files": len(mem_files),
        "total_size_kb": round(total_size / 1024, 1),
        "latest_update": latest_update.strftime("%Y-%m-%d %H:%M") if latest_update else "无",
        "health_score": max(0, score),
        "health_status": status,
        "health_color": color,
        "files": file_list[-10:]
    }


def read_backup_health():
    backups = sorted(BACKUPS_DIR.glob("*.tar.gz"), reverse=True) if BACKUPS_DIR.exists() else []
    if not backups:
        return {"last_backup": None, "count": 0, "health_score": 0, "status": "无备份", "color": "red"}

    latest = backups[0]
    mtime = datetime.fromtimestamp(latest.stat().st_mtime)
    age_hours = (datetime.now() - mtime).total_seconds() / 3600
    size_mb = round(latest.stat().st_size / 1024 / 1024, 1)

    score = 100
    if age_hours > 36: score -= 40
    elif age_hours > 24: score -= 20
    elif age_hours > 12: score -= 10
    if len(backups) < 2: score -= 20

    if score >= 80: status, color = "正常", "green"
    elif score >= 60: status, color = "预警", "yellow"
    else: status, color = "危险", "red"

    return {
        "last_backup": mtime.strftime("%Y-%m-%d %H:%M"),
        "last_backup_age_hours": round(age_hours, 1),
        "file": latest.name,
        "size_mb": size_mb,
        "count": len(backups),
        "health_score": max(0, score),
        "status": status,
        "color": color
    }


def derive_governance():
    system = read_json("system.json") or {}
    oc = system.get("openclaw", {})
    agents = system.get("agents", {})
    backup = system.get("backup", {})
    projects = system.get("projects", {})
    cron = system.get("cronJobs", {})

    last_backup = backup.get("last", {})
    backup_time_str = "未知"
    if last_backup.get("time"):
        try:
            raw = last_backup.get("time", "")
            # Parse various backup time formats
            for fmt in ["%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"]:
                try:
                    backup_dt = datetime.strptime(raw[:19], fmt)
                    backup_time_str = backup_dt.strftime("%Y-%m-%d %H:%M")
                    break
                except ValueError:
                    continue
            else:
                # Fallback: manual parse for "2026:03:25T18:49:19Z"
                m = re.match(r"(\d+):(\d+):(\d+) (\d+):(\d+)", raw)
                if m:
                    y,mo,d,h,mi = m.groups()
                    backup_time_str = f"{y}-{mo}-{d} {h}:{mi}"
                else:
                    backup_time_str = raw[:19]
        except Exception:
            backup_time_str = "未知"

    mem_health = read_memory_health()
    current_model = next((ag.get("model") for ag in derive_agent_architecture()["agents"] if ag.get("model")), "MiniMax-M2.7")
    cron_ok = sum(1 for c in cron.values() if c.get("status") == "ok")

    return {
        "version": oc.get("version", "未知"),
        "git_commit": oc.get("gitCommit", ""),
        "node": oc.get("node", ""),
        "current_project": "stock-assistant",
        "current_channel": "feishu",
        "current_model": current_model,
        "backup_time": backup_time_str,
        "backup_status": last_backup.get("status", "未知"),
        "memory_health": mem_health["health_status"],
        "memory_score": mem_health["health_score"],
        "memory_color": mem_health["health_color"],
        "gateway_status": oc.get("gateway", {}).get("status", "未知"),
        "gateway_pid": oc.get("gateway", {}).get("pid", ""),
        "agent_count": len(derive_agent_architecture()["agents"]),
        "cron_health": f"{cron_ok}/{len(cron)}正常" if cron else "无",
        "project_phase": projects.get("stock-assistant", {}).get("phase", ""),
    }


def derive_approvals():
    tasks = read_json("tasks.json") or {}
    approval_tasks = []
    for status_key in ["todo", "doing"]:
        for task in tasks.get(status_key, []):
            if task.get("approval") or "审批" in task.get("name", ""):
                approval_tasks.append({
                    "task_id": task.get("name", ""),
                    "title": task.get("name", ""),
                    "impact": task.get("impact", "当前流程"),
                    "action_needed": task.get("action_needed", "人工确认"),
                    "date": task.get("date", ""),
                    "workers": task.get("workers", "")
                })
    return {"approvals": approval_tasks, "count": len(approval_tasks)}


def derive_blockers():
    tasks = read_json("tasks.json") or {}
    blocked = tasks.get("blocked", [])
    blockers = []
    for task in blocked:
        blockers.append({
            "task_id": task.get("name", "未知"),
            "title": task.get("name", ""),
            "reason": task.get("blocker_reason", task.get("desc", "未知原因")),
            "workaround": task.get("workaround", "无规避方案"),
            "required_input": task.get("required_input", "待人工输入"),
            "retry_condition": task.get("retry_condition", "人工介入后重试"),
            "impact": task.get("impact", "当前任务"),
            "date": task.get("date", "")
        })
    return {"blockers": blockers, "count": len(blockers)}


def derive_recent_results():
    tasks = read_json("tasks.json") or {}
    done = tasks.get("done", [])
    results = []
    for task in done[-10:]:
        desc = task.get("desc", "")
        git_hash = ""
        if "Git:" in desc:
            parts = desc.split("Git:")
            desc = parts[0].strip()
            git_hash = parts[-1].strip() if len(parts) > 1 else ""
        results.append({
            "title": task.get("name", ""),
            "date": task.get("date", ""),
            "agent": task.get("workers", "主控Agent"),
            "summary": task.get("result", desc),
            "type": task.get("type", "task"),
            "git": git_hash
        })
    return {"results": list(reversed(results)), "count": len(results)}


def derive_recent_exceptions():
    exceptions = []
    for day_offset in range(3):
        day = (datetime.now() - timedelta(days=day_offset)).strftime("%Y-%m-%d")
        mem_file = MEMORY_DIR / f"{day}.md"
        if mem_file.exists():
            content = mem_file.read_text(encoding="utf-8")
            for line in content.split('\n'):
                lower = line.lower()
                if any(kw in lower for kw in ['错误', 'error', '失败', 'failed', '告警', '重试', 'retry', '异常']):
                    if 5 < len(line) < 300:
                        exceptions.append({
                            "message": line.strip()[:200],
                            "date": day,
                            "severity": "high" if any(k in lower for k in ['error', '失败', '异常']) else "medium"
                        })
    return {"exceptions": exceptions[:10], "count": len(exceptions)}


def derive_multi_project():
    system = read_json("system.json") or {}
    projects = system.get("projects", {})
    project_list = []
    for name, info in projects.items():
        project_list.append({
            "name": name,
            "status": info.get("status", "未知"),
            "phase": info.get("phase", ""),
            "created": info.get("created", ""),
            "data_ready": info.get("dataReady", False)
        })
    if not project_list:
        project_list.append({
            "name": "stock-assistant",
            "status": "active",
            "phase": "阶段2 - 核心配置",
            "created": "2026-03-26",
            "data_ready": True
        })
    return {"projects": project_list, "current": "stock-assistant", "count": len(project_list)}


def derive_agent_architecture():
    system = read_json("system.json") or {}
    agents = system.get("agents", {})
    main_info = agents.get("stock-assistant", {})
    sub_agents = main_info.get("agents", [])
    tasks = read_json("tasks.json") or {}
    doing = tasks.get("doing", [])

    role_map = {
        "stock-main": "主控", "stock-research": "研究",
        "stock-exec": "执行", "stock-review": "复盘", "stock-learn": "学习"
    }
    arch = []
    for name in sub_agents:
        is_active = any(
            name.replace("stock-", "") in t.get("workers", "") or name in t.get("name", "")
            for t in doing
        )
        arch.append({
            "name": name,
            "role": role_map.get(name, name),
            "status": "在线" if is_active else "空闲",
            "status_color": "green" if is_active else "gray",
            "last_active": "最近" if is_active else "今日",
            "current_task": "执行中" if is_active else "待命",
        })
    return {"agents": arch, "count": len(arch)}


@app.get("/status/workflow-history")
async def workflow_history():
    """返回所有 workflow 的流转历史"""
    return read_json("workflow_history.json") or {"workflows": []}


def fetch_live_price(code):
    import urllib.request
    if not code:
        return None
    secid = "1." + code if code.startswith("6") else "0." + code
    url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields=f43,f170,f58"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            d = json.loads(r.read()).get("data", {})
        return {"price": d.get("f43", 0) / 100, "pct": d.get("f170", 0) / 100}
    except Exception:
        return None


@app.on_event("startup")
async def startup():
    try:
        result = subprocess.run(["pgrep", "-f", "portal_inbox_server"], capture_output=True, text=True)
        if not result.stdout.strip():
            subprocess.Popen(["python3", "-m", "openclaw", "portal", "start"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


# ─── Legacy endpoints (保持向后兼容) ───────────────────────────────────────

@app.get("/api/status/system")
async def system_status():
    data = read_json("system.json")
    return data if data else {"agents": [], "openclaw": {}}


@app.get("/api/status/tasks")
async def tasks():
    data = read_json("tasks.json")
    return data or {"doing": [], "todo": [], "done": [], "blocked": []}


@app.get("/api/status/portfolio")
async def portfolio():
    data = read_json("portfolio.json")
    if not data:
        return {"holdings": [], "total_value": 0, "total_profit_loss": 0, "summary": {}}
    for h in data.get("holdings", []):
        live = fetch_live_price(h.get("code", ""))
        if live:
            h["price"] = live["price"]
            h["change_pct"] = round(live["pct"], 2)
            h["profit_pct"] = round((live["price"] - h.get("cost", 0)) / max(h.get("cost", 1), 0.01) * 100, 2)
    data["lastUpdated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    return data


@app.get("/api/status/portfolio/history")
async def portfolio_history():
    data = read_json("portfolio_history.json")
    return data if data else {"history": {}, "last_updated": ""}


# ===== holdings.json CRUD =====
@app.get("/api/assets/holdings")
async def get_holdings():
    data = read_data_json("holdings.json")
    if not data:
        return {"holdings": [], "updated": ""}
    for h in data.get("holdings", []):
        code = h.get("code", "")
        if code:
            live = fetch_live_price(code)
            if live:
                h["price"] = live["price"]
                h["change_pct"] = round(live["pct"], 2)
                if h.get("buy_price"):
                    h["profit_pct"] = round((live["price"] - h["buy_price"]) / h["buy_price"] * 100, 2)
    return data

@app.post("/api/assets/add-holding")
async def add_holding(body: dict = None):
    if body is None:
        return {"error": "body required"}
    required = ["code", "name", "shares", "buy_price"]
    for f in required:
        if f not in body:
            return {"error": f"missing field: {f}"}
    data = read_data_json("holdings.json") or {"source": "api", "updated": "", "holdings": []}
    # 检查是否已存在
    for h in data["holdings"]:
        if h.get("code") == body["code"]:
            return {"error": f"已有持仓 {body['code']}，请用 update-holding"}
    h = {
        "code": body["code"],
        "name": body["name"],
        "shares": int(body["shares"]),
        "buy_price": float(body["buy_price"]),
        "buy_date": body.get("buy_date", datetime.now().strftime("%Y-%m-%d")),
        "stop_loss": float(body.get("stop_loss", body["buy_price"] * 0.85)),
        "take_profit": float(body.get("take_profit", body["buy_price"] * 1.20)),
        "risk_status": "持仓中",
        "focus_points": body.get("focus_points", ""),
        "latest_conclusion": body.get("latest_conclusion", ""),
        "suggested_action": body.get("suggested_action", "持有"),
        "last_scan_at": None,
        "status": "pending_scan",
    }
    data["holdings"].append(h)
    data["updated"] = datetime.now().isoformat()
    write_data_json("holdings.json", data)
    return {"ok": True, "holding": h}


@app.post("/api/assets/update-holding")
async def update_holding(body: dict = None):
    if body is None or "code" not in body:
        return {"error": "code required"}
    data = read_data_json("holdings.json")
    if not data:
        return {"error": "holdings.json not found"}
    for h in data["holdings"]:
        if h.get("code") == body["code"]:
            for k, v in body.items():
                if k != "code":
                    h[k] = v
            data["updated"] = datetime.now().isoformat()
            write_data_json("holdings.json", data)
            return {"ok": True, "holding": h}
    return {"error": f"持仓 {body['code']} 不存在"}


# ===== watchlist.json CRUD =====
@app.get("/api/assets/watchlist")
async def get_watchlist():
    return read_data_json("watchlist.json") or {"items": [], "updated": ""}

@app.post("/api/assets/add-watch")
async def add_watch(body: dict = None):
    if body is None:
        return {"error": "body required"}
    required = ["code", "name"]
    for f in required:
        if f not in body:
            return {"error": f"missing field: {f}"}
    data = read_data_json("watchlist.json") or {"source": "api", "updated": "", "items": []}
    for item in data["items"]:
        if item.get("code") == body["code"]:
            return {"error": f"观察池已有 {body['code']}"}
    item = {
        "code": body["code"],
        "name": body["name"],
        "buy_zone": body.get("buy_zone", ""),
        "trigger_condition": body.get("trigger_condition", ""),
        "trend_status": body.get("trend_status", "待观察"),
        "risk_note": body.get("risk_note", ""),
        "latest_conclusion": body.get("latest_conclusion", ""),
        "watch_status": "观察中",
        "remove_reason": None,
        "last_scan_at": None,
        "status": "pending_scan",
    }
    data["items"].append(item)
    data["updated"] = datetime.now().isoformat()
    write_data_json("watchlist.json", data)
    return {"ok": True, "item": item}


@app.post("/api/assets/update-watch")
async def update_watch(body: dict = None):
    if body is None or "code" not in body:
        return {"error": "code required"}
    data = read_data_json("watchlist.json")
    if not data:
        return {"error": "watchlist.json not found"}
    for item in data["items"]:
        if item.get("code") == body["code"]:
            for k, v in body.items():
                if k != "code":
                    item[k] = v
            data["updated"] = datetime.now().isoformat()
            write_data_json("watchlist.json", data)
            return {"ok": True, "item": item}
    return {"error": f"观察池无 {body['code']}"}


# ===== 扫描结果回写 =====
@app.post("/api/assets/scan-result")
async def scan_result(body: dict = None):
    """扫描完成后回写结果到 holdings 或 watchlist"""
    if body is None:
        return {"error": "body required"}
    code = body.get("code")
    item_type = body.get("item_type")  # "holding" or "watch"
    result_fields = {k: v for k, v in body.items() if k not in ("code", "item_type")}
    if not code or not item_type:
        return {"error": "code and item_type required"}
    filename = "holdings.json" if item_type == "holding" else "watchlist.json"
    data = read_data_json(filename)
    if not data:
        return {"error": f"{filename} not found"}
    target_list = data.get("holdings" if item_type == "holding" else "items", [])
    for item in target_list:
        if item.get("code") == code:
            for k, v in result_fields.items():
                item[k] = v
            item["last_scan_at"] = datetime.now().isoformat()
            item["status"] = "scanned"
            data["updated"] = datetime.now().isoformat()
            write_data_json(filename, data)
            return {"ok": True, "item": item}
    return {"error": f"{code} not found in {filename}"}


@app.get("/api/assets/sync")
async def sync_assets():
    """全量同步：返回所有 holdings + watchlist 合并状态"""
    holdings = read_data_json("holdings.json")
    watchlist = read_data_json("watchlist.json")
    result = {
        "sync_at": datetime.now().isoformat(),
        "holdings": [],
        "watchlist": [],
    }
    # 合并持仓含watchlist中的股票
    codes = set()
    if holdings:
        for h in holdings.get("holdings", []):
            codes.add(h.get("code"))
            live = fetch_live_price(h.get("code", "")) if h.get("code") else None
            item = dict(h)
            if live:
                item["price"] = live["price"]
                item["change_pct"] = round(live["pct"], 2)
                item["profit_pct"] = round((live["price"] - h.get("buy_price", 0)) / max(h.get("buy_price", 1), 0.01) * 100, 2)
            result["holdings"].append(item)
    if watchlist:
        for w in watchlist.get("items", []):
            if w.get("code") not in codes:
                codes.add(w.get("code"))
                live = fetch_live_price(w.get("code", "")) if w.get("code") else None
                item = dict(w)
                if live:
                    item["price"] = live["price"]
                    item["change_pct"] = round(live["pct"], 2)
                result["watchlist"].append(item)
    return result


@app.get("/api/assets/recent-scans")
async def recent_scans(code: str = None, item_type: str = None):
    """最近扫描记录"""
    if not code:
        return {"error": "code required"}
    # 从 scan_history.json 读取
    history = read_data_json("scan_history.json") or {}
    records = []
    for date, scans in history.items():
        for scan in scans:
            if scan.get("code") == code:
                if item_type and scan.get("item_type") != item_type:
                    continue
                records.append({"date": date, **scan})
    records.sort(key=lambda x: x.get("date", ""), reverse=True)
    return {"code": code, "item_type": item_type, "records": records[:20]}


@app.get("/api/assets/related-records")
async def related_records(code: str = None, item_type: str = None):
    """关联记录：某股票相关的所有操作/扫描记录"""
    if not code:
        return {"error": "code required"}
    # 从 scan_history.json 读取所有相关记录
    history = read_data_json("scan_history.json") or {}
    records = []
    for date, scans in history.items():
        for scan in scans:
            if scan.get("code") == code:
                if item_type and scan.get("item_type") != item_type:
                    continue
                records.append({"date": date, **scan})
    records.sort(key=lambda x: x.get("date", ""), reverse=True)
    return {"code": code, "item_type": item_type, "records": records[:50]}


@app.get("/api/status/all")
async def all_status():
    # 持仓数据：合并原始数据 + 实时价格（调用 price fetch 逻辑）
    portfolio_raw = read_json("portfolio.json") or {}
    holdings = portfolio_raw.get("holdings", [])
    for h in holdings:
        code = h.get("code", "")
        if code:
            live = fetch_live_price(code)
            if live:
                h["price"] = live["price"]
                h["change_pct"] = round(live["pct"], 2)
                h["profit_pct"] = round((live["price"] - h.get("cost", 0)) / max(h.get("cost", 1), 0.01) * 100, 2)
    portfolio_result = {
        "holdings": holdings,
        "source": portfolio_raw.get("source", "未知"),
        "updated": portfolio_raw.get("updated", ""),
        "lastUpdated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "note": portfolio_raw.get("note", ""),
    }

    return {
        "tasks": read_json("tasks.json") or {},
        "portfolio": portfolio_result,
        "portfolio_history": read_json("portfolio_history.json") or {},
        "server_time": datetime.now().isoformat(),
        "governance": derive_governance(),
        "approvals": derive_approvals(),
        "blockers": derive_blockers(),
        "recent_results": derive_recent_results(),
        "recent_exceptions": derive_recent_exceptions(),
        "backup_health": read_backup_health(),
        "memory_health": read_memory_health(),
        "changelog_summary": read_changelog_summary(),
        "multi_project": derive_multi_project(),
        "agent_architecture": derive_agent_architecture(),
    }


# ─── New observability API endpoints ──────────────────────────────────────

@app.get("/api/status/governance")
async def governance():
    return derive_governance()


@app.get("/api/status/approvals")
async def approvals():
    return derive_approvals()


@app.get("/api/status/blockers")
async def blockers():
    return derive_blockers()


@app.get("/api/status/recent-results")
async def recent_results():
    return derive_recent_results()


@app.get("/api/status/recent-exceptions")
async def recent_exceptions():
    return derive_recent_exceptions()


@app.get("/api/status/backup-health")
async def backup_health():
    return read_backup_health()


@app.get("/api/status/memory-health")
async def memory_health():
    return read_memory_health()


@app.get("/api/status/changelog-summary")
async def changelog_summary():
    return {"changes": read_changelog_summary()}


@app.get("/api/status/multi-project")
async def multi_project():
    return derive_multi_project()


@app.get("/api/status/agent-architecture")
async def agent_architecture():
    return derive_agent_architecture()


@app.get("/api/price/{code}")
async def get_live_price(code: str):
    secid = "1." + code if code.startswith("6") else "0." + code
    url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields=f43,f170,f58"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            d = json.loads(r.read()).get("data", {})
        return {"code": code, "name": d.get("f58", code), "price": d.get("f43", 0) / 100, "pct": d.get("f170", 0) / 100}
    except Exception as e:
        return {"error": str(e)}


@app.get("/")
async def index():
    html_path = TEMPLATES_DIR / "portal.html"
    if html_path.exists():
        return FileResponse(html_path, headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        })
    return HTMLResponse(content="<h1>Portal not ready</h1>", status_code=503)


@app.get("/static/{filename}")
async def static_files(filename: str):
    return FileResponse(STATIC_DIR / filename)


if __name__ == "__main__":
    import uvicorn
    print(f"Starting OpenClaw Portal on http://localhost:{PORT}")
    print(f"Status files: {STATUS_DIR}")
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
