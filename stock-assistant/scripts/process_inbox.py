#!/usr/bin/env python3
"""
process_inbox.py - 任务接收与转发（已重构：使用 dispatcher.py）

注意：spawn 操作仍在 main 上下文执行（OpenClaw 架构限制），
但通过 dispatcher.py 写入 workflow_history，
确保 dispatchedBy = "stock-main"（项目级主控身份）

架构分工：
- main（系统层）：接收任务、调用 dispatcher.py、写入 system.json
- stock-main（项目层）：业务理解、任务分类、派发决策（dispatcher.py 执行）
- inbox 文件：作为 main → stock-main 的任务传递队列
"""
import subprocess, socket, os, json, shutil, sys
from datetime import datetime

INBOX_DIR  = "/home/admin/openclaw/workspace/stock-assistant/tasks/inbox"
TODO_DIR   = "/home/admin/openclaw/workspace/stock-assistant/tasks/todo"
TASKS_JSON = "/home/admin/openclaw/workspace/portal/status/tasks.json"
TRIGGER_FILE = "/home/admin/openclaw/workspace/stock-assistant/tasks/.pending_dispatch.json"
WORKSPACE  = "/home/admin/openclaw/workspace"
DISPATCHER = "/home/admin/openclaw/workspace/stock-assistant/scripts/dispatcher.py"

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

def dispatch_via_dispatcher(name, content, complexity):
    """
    通过 dispatcher.py 派发任务
    dispatchedBy 始终为 stock-main（由 dispatcher.py 保证）
    """
    try:
        result = subprocess.run([
            "python3", DISPATCHER,
            "--dispatch", name, content[:200]
        ], capture_output=True, text=True, timeout=30)
        
        output = result.stdout.strip()
        if result.returncode == 0 and output:
            return True, output
        else:
            return False, f"dispatcher返回码 {result.returncode}: {result.stderr[:100]}"
    except Exception as e:
        return False, str(e)

def main():
    ensure_inbox_server()

    if not os.path.exists(INBOX_DIR):
        return {"action": "no_inbox"}

    inbox_files = sorted([f for f in os.listdir(INBOX_DIR) if f.endswith(".md")])
    if not inbox_files:
        pending = load_pending()
        for item in pending[:]:
            ok, msg = dispatch_via_dispatcher(item["name"], item["content"], item["complexity"])
            if ok:
                pending.remove(item)
                print(f"✅ [stock-main] {msg}")
            else:
                print(f"⚠️ 分发失败: {msg}")
        save_pending(pending)
        return {"action": "idle"}

    tasks = load_pending()
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
            workers = "stock-main → stock-research → stock-exec → stock-review → stock-learn"
            result = "派发中（dispatchedBy=stock-main）"
            # 立即通过 dispatcher 派发完整 pipeline
            ok, msg = dispatch_via_dispatcher(name, content, complexity)
            if ok:
                print(f"✅ [stock-main] pipeline已启动: {msg}")
            else:
                print(f"⚠️ 分发失败: {msg}")
        else:
            workers = "stock-main（直接处理）"
            result = "主控处理中"
            dispatch_via_dispatcher(name, content, "simple")

        # 更新 tasks.json
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
    print(f"处理了 {len(inbox_files)} 个任务，{len(tasks)} 个待分发")

if __name__ == "__main__":
    main()

def silent_main():
    """静默模式：有任务才输出，无任务完全静默"""
    sys.stdout = open('/dev/null', 'w')
    sys.stderr = open('/dev/null', 'w')
    main()

if __name__ == "__main__":
    import sys
    if "--silent" in sys.argv:
        silent_main()
    else:
        main()
