#!/usr/bin/env python3
"""
process_inbox.py - 任务接收与中转（v3: sessions_send 到 stock-main）

架构链路：
  inbox文件 → process_inbox扫描 → 写 tasks/pending_stock_main.json
    → main agent下次心跳 → sessions_send(stock-main-session, task)
      → stock-main session接收 → dispatcher.py执行派发
        → spawned子agent（dispatchedBy=stock-main）

注意：
- sessions_send 是 agent runtime 工具，subprocess无法直接调用
- 因此 process_inbox 只负责写队列，真正的 sessions_send 由 main agent 执行
- stock-main session key 硬编码（见 STOCK_MAIN_SESSION常量）
"""
import subprocess, socket, os, json, shutil, sys, time
from datetime import datetime
from pathlib import Path

INBOX_DIR      = "/home/admin/openclaw/workspace/stock-assistant/tasks/inbox"
TODO_DIR       = "/home/admin/openclaw/workspace/stock-assistant/tasks/todo"
TASKS_JSON     = "/home/admin/openclaw/workspace/portal/status/tasks.json"
TRIGGER_FILE   = "/home/admin/openclaw/workspace/stock-assistant/tasks/.pending_dispatch.json"
QUEUE_FILE     = "/home/admin/openclaw/workspace/stock-assistant/tasks/pending_stock_main.json"
WORKSPACE      = "/home/admin/openclaw/workspace"
DISPATCHER     = "/home/admin/openclaw/workspace/stock-assistant/scripts/dispatcher.py"

# stock-main session key（当前无可用持久session，通过dispatcher.py直接派发）
# sessions_spawn在main上下文执行，dispatcher.py保证dispatchedBy=stock-main
STOCK_MAIN_SESSION = None

COMPLEX_KEYWORDS = ["分析","研究","策略","规划","设计","回测","搭建","实现","系统","对比","review"]
SIMPLE_KEYWORDS  = ["查","看","检查","更新","记录","刷新","关闭","完成"]

def ensure_inbox_server():
    """检查 inbox server 是否在运行（端口 18790）"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        r = sock.connect_ex(("127.0.0.1", 18790))
        sock.close()
        if r != 0:
            print("[inbox] port 18790 not listening, skipping server start")
    except Exception:
        print("[inbox] socket check failed, skipping")

def classify_task(name):
    score_c = sum(1 for k in COMPLEX_KEYWORDS if k in name)
    score_s = sum(1 for k in SIMPLE_KEYWORDS  if k in name)
    return "complex" if score_c > score_s else "simple"

def load_pending():
    if os.path.exists(TRIGGER_FILE):
        with open(TRIGGER_FILE) as f:
            return json.load(f)
    return []

def save_pending(pending):
    with open(TRIGGER_FILE, "w") as f:
        json.dump(pending, f, ensure_ascii=False, indent=2)

def load_queue():
    if not os.path.exists(QUEUE_FILE):
        return []
    with open(QUEUE_FILE) as f:
        content = f.read().strip()
        if not content:
            return []
        return json.loads(content)

def save_queue(queue):
    with open(QUEUE_FILE, "w") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)

def enqueue_for_stock_main(task_name, task_content, complexity, task_id):
    """
    将任务写入 pending_stock_main.json 队列
    main agent 会读取此队列并通过 sessions_send 发送给 stock-main
    """
    queue = load_queue()
    queue.append({
        "id": task_id,
        "name": task_name,
        "content": task_content,
        "complexity": complexity,
        "enqueuedAt": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "status": "pending_dispatch",
        "dispatchedBy": "stock-main",
        "sessionKey": STOCK_MAIN_SESSION
    })
    save_queue(queue)

def dispatch_direct(name, content, complexity):
    """
    直接调用 dispatcher.py 派发任务。
    dispatcher.py 的 DISPATCHER_ID="stock-main" 硬编码，所以 dispatchedBy 始终是 stock-main。
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dispatcher = os.path.join(script_dir, "dispatcher.py")
    result = subprocess.run(
        [sys.executable, dispatcher, "--dispatch", name, content],
        capture_output=True, text=True, timeout=120,
        cwd=script_dir
    )
    if result.returncode == 0:
        return True, result.stdout.strip()
    else:
        return False, result.stderr.strip()[:200]

def main():
    ensure_inbox_server()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"[{ts}] process_inbox.py invoked", flush=True)

    if not os.path.exists(INBOX_DIR):
        print(f"[{ts}] inbox目录不存在", flush=True)
        return {"action": "no_inbox"}

    inbox_files = sorted([f for f in os.listdir(INBOX_DIR) if f.endswith(".md")])
    if not inbox_files:
        print(f"[{ts}] inbox空，触发 inbox-disp.js 补货", flush=True)
        # inbox 空时，调用 inbox-disp.js 执行补货逻辑
        disp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts", "inbox-disp.js")
        try:
            r = subprocess.run(["node", disp_path], capture_output=True, text=True, timeout=30)
            if r.stdout.strip():
                result = json.loads(r.stdout.strip())
                print(f"[{ts}] inbox-disp: {result.get('action')} {result.get('taskType','')} {result.get('taskId','')}", flush=True)
                return result
        except Exception as e:
            print(f"[{ts}] inbox-disp 调用失败: {e}", flush=True)
        return {"action": "idle"}

    tasks = load_pending()
    queue  = load_queue()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")

    for fname in inbox_files:
        src = os.path.join(INBOX_DIR, fname)
        dst = os.path.join(TODO_DIR, fname)
        with open(src) as sf:
            content = sf.read()
        name = content.split("\n")[0].replace("#", "").strip()
        shutil.move(src, dst)

        complexity = classify_task(name)
        task_id = fname.replace(".md", "")

        if complexity == "complex":
            tasks.append({"id": task_id, "name": name, "content": content, "complexity": complexity})
            workers = "stock-main（通过dispatcher派发，dispatchedBy=stock-main硬编码）"
            result = "派发中"
            ok, msg = dispatch_direct(name, content, complexity)
            if ok:
                print(f"✅ [stock-main] {msg}")
                # 更新队列状态为 dispatched
                queue = load_queue()
                for item in queue:
                    if item["id"] == task_id:
                        item["status"] = "dispatched"
                        item["dispatchedAt"] = datetime.now().isoformat()
                        break
                save_queue(queue)
            else:
                print(f"⚠️ 派发失败: {msg}")
        else:
            workers = "stock-main（直接处理）"
            result = "主控处理中"
            dispatch_direct(name, content, "simple")

        tasks_js = {}
        if os.path.exists(TASKS_JSON):
            with open(TASKS_JSON) as f:
                tasks_js = json.load(f)
        tasks_js.setdefault("todo", [])
        tasks_js.setdefault("doing", [])
        tasks_js.setdefault("done", [])
        tasks_js["todo"].insert(0, {
            "id": task_id, "name": name, "date": ts, "workers": workers,
            "desc": f"复杂度: {complexity}", "result": result,
            "dispatchedBy": "stock-main"
        })
        tasks_js["lastUpdated"] = ts
        with open(TASKS_JSON, "w") as f:
            json.dump(tasks_js, f, ensure_ascii=False, indent=2)

    save_pending(tasks)
    q_len = len(load_queue())
    print(f"处理了 {len(inbox_files)} 个任务，{len(tasks)} 个待分发，队列积压 {q_len} 条")

if __name__ == "__main__":
    main()
