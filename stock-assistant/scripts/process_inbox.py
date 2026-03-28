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

# stock-main 持久 session（在 stock-main 成功建立后更新此处）
STOCK_MAIN_SESSION = "agent:main:subagent:8f790cd7-94b2-405b-9e48-b66bea30128c"

COMPLEX_KEYWORDS = ["分析","研究","策略","规划","设计","回测","搭建","实现","系统","对比","review"]
SIMPLE_KEYWORDS  = ["查","看","检查","更新","记录","刷新","关闭","完成"]

def ensure_inbox_server():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        r = sock.connect_ex(("127.0.0.1", 18790))
        sock.close()
        if r != 0:
            raise Exception("not listening")
    except Exception:
        subprocess.Popen(
            ["python3", "/home/admin/openclaw/workspace/scripts/portal_inbox_server.py"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

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
    if os.path.exists(QUEUE_FILE):
        with open(QUEUE_FILE) as f:
            return json.load(f)
    return []

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
    直接通过 dispatcher 派发（dispatchedBy=stock-main，已建立 session）
    用于 complex 任务：通过 stock-main session 的 subprocess 执行
    """
    try:
        result = subprocess.run([
            "python3", DISPATCHER,
            "--dispatch", name, content[:500]
        ], capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            return False, f"dispatcher返回码 {result.returncode}"
    except Exception as e:
        return False, str(e)

def main():
    ensure_inbox_server()

    if not os.path.exists(INBOX_DIR):
        return {"action": "no_inbox"}

    inbox_files = sorted([f for f in os.listdir(INBOX_DIR) if f.endswith(".md")])
    if not inbox_files:
        # 检查待分发队列
        pending = load_pending()
        for item in pending[:]:
            ok, msg = dispatch_direct(item["name"], item["content"], item["complexity"])
            if ok:
                pending.remove(item)
                print(f"✅ [stock-main] {msg}")
            else:
                print(f"⚠️ 分发失败: {msg}")
        save_pending(pending)
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
            workers = "main → stock-main(session) → research→exec→review→learn"
            result = "派发中（sessions_send→stock-main→dispatcher→dispatchedBy=stock-main）"
            # 尝试直接通过 stock-main session 执行 dispatcher
            ok, msg = dispatch_direct(name, content, complexity)
            if ok:
                print(f"✅ [stock-main] {msg}")
                # 同时写入队列（main agent 感知到任务）
                enqueue_for_stock_main(name, content, complexity, task_id)
            else:
                print(f"⚠️ 直接派发失败，队列备选: {msg}")
                enqueue_for_stock_main(name, content, complexity, task_id)
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

def silent_main():
    sys.stdout = open('/dev/null', 'w')
    sys.stderr = open('/dev/null', 'w')
    main()

if __name__ == "__main__":
    if "--silent" in sys.argv:
        silent_main()
    else:
        main()
