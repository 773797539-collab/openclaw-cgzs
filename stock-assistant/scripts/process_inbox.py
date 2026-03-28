#!/usr/bin/env python3
"""
process_inbox.py - 任务分发中心
收到任务 → 写触发文件 → 主 agent 下次心跳时真正分发
"""
import subprocess, socket, os, json, shutil
from datetime import datetime

INBOX_DIR  = "/home/admin/openclaw/workspace/stock-assistant/tasks/inbox"
TODO_DIR   = "/home/admin/openclaw/workspace/stock-assistant/tasks/todo"
TASKS_JSON = "/home/admin/openclaw/workspace/portal/status/tasks.json"
TRIGGER_FILE = "/home/admin/openclaw/workspace/stock-assistant/tasks/.pending_dispatch.json"
WORKSPACE  = "/home/admin/openclaw/workspace"

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
            # inbox server未运行，无需操作
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

def dispatch_task(name, content, complexity):
    """通过 openclaw sessions spawn 启动子 agent"""
    label = f"dispatch-{datetime.now().strftime('%H%M%S')}"
    if complexity == "complex":
        agent_id = "stock-research"
        workers = "主控 → stock-research → stock-exec → stock-review"
    else:
        agent_id = "stock-main"
        workers = "主控 Agent (直接处理)"

    try:
        subprocess.run([
            "openclaw", "sessions", "spawn",
            "--label", label,
            "--runtime", "subagent",
            "--run-timeout", "600",
            "--task", f"# 任务\n\n{name}\n\n## 详情\n{content[:800]}"
        ], capture_output=True, timeout=10)
        return True, f"已分发 → {agent_id}"
    except Exception as e:
        return False, str(e)

def main():
    ensure_inbox_server()

    if not os.path.exists(INBOX_DIR):
        return {"action": "no_inbox"}

    inbox_files = sorted([f for f in os.listdir(INBOX_DIR) if f.endswith(".md")])
    if not inbox_files:
        # 检查是否有待分发的复杂任务（简单任务直接做）
        pending = load_pending()
        for item in pending[:]:
            ok, msg = dispatch_task(item["name"], item["content"], item["complexity"])
            if ok:
                pending.remove(item)
                print(f"✅ {msg}: {item['name']}")
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
            workers = "主控 → stock-research → stock-exec → stock-review"
            result = "待分发至研究 Agent"
        else:
            # 简单任务直接处理
            workers = "主控 Agent (直接处理)"
            result = "主控处理中"
            # 立即分发
            dispatch_task(name, content, "simple")

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
            "desc": f"复杂度: {complexity}", "result": result
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
    import sys
    sys.stdout = open('/dev/null', 'w')
    sys.stderr = open('/dev/null', 'w')
    main()

if __name__ == "__main__":
    import sys
    if "--silent" in sys.argv:
        silent_main()
    else:
        main()
