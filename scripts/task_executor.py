#!/usr/bin/env python3
"""
task_executor.py - 持续自驱任务执行器
每完成一个任务，立即检查并补货/派发下一任务，
不等待 daemon tick / heartbeat / 定时触发。
"""
import os, json, subprocess, time, sys
from datetime import datetime
from pathlib import Path

WORKSPACE      = "/home/admin/openclaw/workspace"
STOCK_WS      = f"{WORKSPACE}/stock-assistant"
SCRIPTS_DIR   = f"{WORKSPACE}/scripts"
DOING_DIR     = f"{STOCK_WS}/tasks/doing"
DONE_DIR      = f"{STOCK_WS}/tasks/done"
TODO_DIR      = f"{STOCK_WS}/tasks/todo"
INBOX_DIR     = f"{STOCK_WS}/tasks/inbox"
NODE_BIN      = "/home/admin/.nvm/versions/node/v24.14.0/bin/node"

# ===== 运行参数 =====
MAX_BATCH     = 1000   # 每轮最大批量（保护 token，1000=近似无限）
TOKEN_STOP    = 0.20   # token 剩余 ≤20% 时停止
LOOP_SLEEP      = 1      # 每轮循环间隙（秒）
CORE_IDLE_SLEEP = 180    # inbox-disp idle 时休眠（秒），等待冷却到期
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
        reason  = j.get("reason","")
        if action == "idle":
            log(f"inbox-disp: idle ({reason})")
            return None  # 全部冷却中，不计入批次
        log(f"inbox-disp: {action} {task_id}")
        return task_id if action in ("dispatched","replenished") else None
    except:
        log(f"inbox-disp parse error: {r.stdout[:100]}")
        return None

# ===== 任务处理器 =====
# ===== 主执行链白名单（只有这些任务才会被处理）=====
TASK_HANDLERS = {
    "持仓扫描":      "execute_portfolio_scan",
    "持仓风险更新":  "execute_portfolio_scan",
    "观察池扫描":    "execute_portfolio_scan",
    "holdings更新": "execute_portfolio_scan",
    "watchlist更新": "execute_portfolio_scan",
}
# 不在白名单内的任务类型 → 完全跳过（不进done，不报错）

def execute_diagnostic(task_id, content):
    return {}  # 空结果，不进done

def execute_portfolio_scan(task_id, content):
    """扫描持仓或观察池，回写 scan_result 到 data JSON"""
    import datetime as dt

    # 解析 task_type 和 code
    task_type = "all"
    code = None
    for line in content.split("\n"):
        if ":" in line:
            k, v = line.split(":", 1)
            k = k.strip()
            v = v.strip()
            if k in ("type", "t"):
                if v in ("持仓扫描", "持仓风险更新", "holdings更新"):
                    task_type = "holding"
                elif v in ("观察池扫描", "watchlist更新"):
                    task_type = "watch"
            if k == "code":
                code = v

    DATA_DIR = Path("/home/admin/openclaw/workspace/stock-assistant/data")

    def read_json(fname):
        path = DATA_DIR / fname
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return None

    def write_json(fname, data):
        path = DATA_DIR / fname
        with open(path, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    now = dt.datetime.now().isoformat()

    # Fallback：用 data JSON 里的已有数据生成结论
    result = None
    if task_type == "holding":
        data = read_json("holdings.json")
        if data:
            for h in data.get("holdings", []):
                if not code or h.get("code") == code:
                    buy_price = h.get("buy_price", 0)
                    price = h.get("price") or buy_price
                    profit_pct = round((price - buy_price) / buy_price * 100, 2) if buy_price else 0
                    stop_loss = h.get("stop_loss", buy_price * 0.85)
                    take_profit = h.get("take_profit", buy_price * 1.20)
                    if price <= stop_loss:
                        risk_status = "STOP_LOSS_HIT"
                        action = "建议止损出局"
                    elif profit_pct >= 5:
                        risk_status = "PROFIT_GOOD"
                        action = "持有，关注止盈"
                    elif profit_pct >= 0:
                        risk_status = "PROFIT"
                        action = "持有"
                    elif profit_pct >= -10:
                        risk_status = "LOSS_LARGE"
                        action = "持有，关注止损线"
                    else:
                        risk_status = "NEAR_STOP_LOSS"
                        action = "密切监控"

                    direction = "盈" if profit_pct >= 0 else "亏"
                    conclusion = (
                        h["name"] + "(" + h["code"] + ")：" +
                        "现价¥" + str(round(price, 2)) + "，" +
                        "浮" + direction + str(abs(profit_pct)) + "%(" +
                        str(round((price - buy_price) * h.get("shares", 0), 0)) + "元)。" +
                        "止损¥" + str(stop_loss) + "，止盈¥" + str(take_profit) + "。" +
                        "风险状态：" + risk_status + "。建议：" + action + "。"
                    )
                    h["risk_status"] = risk_status
                    h["latest_conclusion"] = conclusion
                    h["suggested_action"] = action
                    h["last_scan_at"] = now
                    h["status"] = "scanned"
                    write_json("holdings.json", data)
                    result = {"code": h["code"], "conclusion": conclusion, "action": action, "risk_status": risk_status}
                    break
    elif task_type == "watch":
        data = read_json("watchlist.json")
        if data:
            for w in data.get("items", []):
                if not code or w.get("code") == code:
                    conclusion = (
                        w["name"] + "(" + w["code"] + ")：" +
                        "买入区间" + w.get("buy_zone", "?") + "，" +
                        "触发条件" + w.get("trigger_condition", "?") + "。" +
                        "趋势：" + w.get("trend_status", "?") + "。" +
                        "风险：" + w.get("risk_note", "?") + "。"
                    )
                    w["latest_conclusion"] = conclusion
                    w["watch_status"] = "OBSERVING"
                    w["last_scan_at"] = now
                    w["status"] = "scanned"
                    write_json("watchlist.json", data)
                    result = {"code": w["code"], "conclusion": conclusion, "action": "观察", "risk_status": w.get("trend_status", "?")}
                    break

    if result:
        log("execute_portfolio_scan 完成: " + json.dumps(result, ensure_ascii=False)[:150])
    return result or {"error": "no data found"}

def execute_lightweight(task_id, content):
    """轻量任务：不产生真实结果，不进done统计"""
    return None  # has_meaningful_result 会返回 False，skip_task

# ===== P0 股票任务结果处理器 =====
def check_and_notify_p0(task_id, task_type, result_data):
    """
    判断 P0 任务结果是否需要通知用户。
    返回 (should_notify, notify_message)
    通知条件：
    - 持仓风险状态变化（止损/止盈建议变化）
    - 观察池新增/移除/升级
    - 盘前/盘后结论生成
    - 盘中强时效提醒
    - 资产中心数据变化
    """
    # 通知消息收集
    alerts = []

    # === 持仓风险更新 ===
    if task_type == '持仓风险更新' and result_data:
        try:
            # 读取持仓数据
            portfolio_file = f"{WORKSPACE}/stock-assistant/data/portfolio.json"
            if os.path.exists(portfolio_file):
                with open(portfolio_file) as f:
                    pf = json.load(f)
                holdings = pf.get('holdings', [])
                if holdings:
                    h = holdings[0]
                    price   = float(h.get('price', 0))
                    cost    = float(h.get('cost', 0))
                    shares  = int(h.get('shares', 0))
                    if cost > 0:
                        pct = (price - cost) / cost * 100
                        stop_loss = cost * 0.85  # -15%
                        if pct <= -10:
                            alerts.append(f"⚠️ 持仓风险：{h.get('name','?')} 浮亏 {pct:.1f}%，距止损线 {stop_loss:.2f} 还有 {pct+15:.1f}%")
                        if pct >= 5:
                            alerts.append(f"✅ 持仓提醒：{h.get('name','?')} 已浮盈 {pct:.1f}%，关注止盈时机")
        except Exception as e:
            log(f"持仓风险读取失败: {e}")
        if alerts:
            return True, '\n'.join(alerts)

    # === 观察池扫描 ===
    if task_type == '观察池扫描' and result_data:
        try:
            watchlist_file = f"{WORKSPACE}/stock-assistant/data/watchlist.json"
            if os.path.exists(watchlist_file):
                with open(watchlist_file) as f:
                    wl = json.load(f)
                items = wl.get('items', []) if isinstance(wl, dict) else (wl or [])
                if items:
                    names = [h.get('name', h.get('code', '?')) for h in items[:5]]
                    alerts.append(f"📋 观察池 ({len(items)}只): {', '.join(names)}")
        except Exception as e:
            log(f"观察池读取失败: {e}")
        if alerts:
            return True, '\n'.join(alerts)

    # === 盘前任务 ===
    if task_type in ('市场环境判断', '热点板块', '今日重点3股', '行动计划') and result_data:
        try:
            market_file = f"{WORKSPACE}/stock-assistant/data/market-brief.json"
            if os.path.exists(market_file):
                with open(market_file) as f:
                    mb = json.load(f)
                brief = mb.get('brief', mb.get('summary', ''))
                if brief:
                    alerts.append(f"📊 {task_type}：{brief[:200]}")
        except:
            pass
        if alerts:
            return True, '\n'.join(alerts)

    # === 盘后复盘 ===
    if task_type in ('市场复盘', '持仓复盘', '选股复盘', '错误归因', '次日准备') and result_data:
        try:
            review_file = f"{WORKSPACE}/stock-assistant/data/review.json"
            if os.path.exists(review_file):
                with open(review_file) as f:
                    rv = json.load(f)
                summary = rv.get('summary', rv.get('conclusion', ''))
                if summary:
                    alerts.append(f"📝 {task_type}：{summary[:200]}")
        except:
            pass
        if alerts:
            return True, '\n'.join(alerts)

    # === 强时效提醒 ===
    if task_type == '强时效提醒' and result_data:
        # 强时效提醒默认通知
        return True, f"🚨 {result_data.get('summary', '有待处理事项')}" if isinstance(result_data, dict) else f"🚨 强时效提醒"

    # === holdings / watchlist 更新 ===
    if task_type in ('holdings更新', 'watchlist更新', 'related记录', 'recent扫描') and result_data:
        if result_data and result_data.get('updated'):
            return True, f"✅ {task_type} 已更新"

    return False, ''

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

# 诊断关键字：出现这些说明是 diagnostic 空壳输出
DIAG_KEYWORDS = ['mcp_205', 'mcp_206', 'inbox_daemon', 'gateway', 'STOPPED', 'running', 'HTTPError', 'URLError']

def has_meaningful_result(result_data):
    """判断 result 是否有真实业务内容，而非诊断空壳"""
    if not result_data:
        return False
    if isinstance(result_data, dict):
        # error dict 不是真实结果
        if "error" in result_data and not result_data.get("conclusion"):
            return False
        result_str = json.dumps(result_data)
        if any(kw in result_str for kw in DIAG_KEYWORDS):
            return False
        if not result_data:
            return False
        return True
    return False

def skip_task(task_id, reason="无真实业务结果"):
    """跳过任务：不写入done，只清理doing"""
    for suffix in [".md", ".running"]:
        f = os.path.join(DOING_DIR, task_id + suffix)
        if os.path.exists(f):
            os.unlink(f)
    log(f"跳过: {task_id} ({reason})")

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
            log(f"Token {token_ratio:.1%} ≤ {TOKEN_STOP:.0%}，退出循环")
            break

        # 2. 找 doing 中最老任务
        files = [f for f in os.listdir(DOING_DIR) if f.endswith(".md")]
        if not files:
            # doing 空：调用 inbox-disp 补货+派发
            idle_reason = dispatch_one()
            if idle_reason is None:
                # inbox-disp idle（全部冷却中）：休眠 CORE_IDLE_SLEEP 秒
                time.sleep(CORE_IDLE_SLEEP)
                continue
            # inbox-disp 已派发，doing 已有任务，继续执行
            files = [f for f in os.listdir(DOING_DIR) if f.endswith(".md")]
            if not files:
                time.sleep(LOOP_SLEEP)
                continue

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
        else:
            # 不在白名单 → 静默废弃（不写任何日志，不进done/todo）
            try:
                os.remove(doing_file)
                if os.path.exists(running_file):
                    os.remove(running_file)
            except:
                pass
            continue  # 跳过，不计入 batch_count

        # 判断：有真实结果才进 done，否则跳过
        if has_meaningful_result(result_data):
            move_to_done(task_id, content, result_data)
        else:
            skip_task(task_id, "无真实业务结果")
        batch_count += 1

        # 判断是否需要通知用户
        should_notify, notify_msg = check_and_notify_p0(task_id, task_type, result_data)
        if should_notify and notify_msg:
            # P0 重要结果写入通知队列，由 agent heartbeat 时推送
            notify_file = f"{WORKSPACE}/data/p0-notifications.jsonl"
            os.makedirs(os.path.dirname(notify_file), exist_ok=True)
            with open(notify_file, 'a') as f:
                f.write(json.dumps({
                    "task_id": task_id,
                    "task_type": task_type,
                    "message": notify_msg,
                    "ts": datetime.now().isoformat(),
                    "priority": "P0"
                }, ensure_ascii=False) + '\n')

        # 3. 立即检查 todo 水位：低于 TODO_WATER 立即补货
        todo_count = len([f for f in os.listdir(TODO_DIR) if f.endswith(".md")])
        if todo_count < TODO_WATER:
            log(f"todo={todo_count} < 水位{TODO_WATER}，补货")
            dispatch_one()  # replenish

    log(f"循环结束: {batch_count} 个任务")
    return batch_count

if __name__ == "__main__":
    count = run_batch()
    log(f"本轮执行 {count} 个任务，退出")
    sys.exit(0)

# ===== 进程锁：防止多实例 =====
LOCK_FILE = "/tmp/task_executor.lock"
def acquire_lock():
    import fcntl
    try:
        fd = open(LOCK_FILE, 'w')
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fd.write(str(os.getpid()))
        fd.flush()
        return fd
    except (IOError, OSError):
        return None

lock_fd = acquire_lock()
if lock_fd is None:
    print("[task_exec] 已有实例在运行，退出")
    sys.exit(0)
