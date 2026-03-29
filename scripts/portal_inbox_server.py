#!/usr/bin/env python3
"""
portal_inbox_server.py - 纯 stdlib HTTP 服务器（替代 Flask/Werkzeug）
端口: 18790
提供:
  GET  /health        - 健康检查
  GET  /list          - 任务列表
  GET  /get?id=<id>   - 获取任务内容
  POST /snapshot      - 触发 snapshot.js，更新 portal/status/tasks.json
"""
import json, os, threading, http.server, socketserver, subprocess
from datetime import datetime

PORT = 18790
INBOX_DIR = "/home/admin/openclaw/workspace/stock-assistant/tasks/inbox"
os.makedirs(INBOX_DIR, exist_ok=True)

class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # 静默日志

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        elif self.path == "/list" or self.path == "/list/":
            tasks = []
            for fn in sorted(os.listdir(INBOX_DIR)):
                if fn.endswith(".md"):
                    fp = os.path.join(INBOX_DIR, fn)
                    tasks.append({
                        "id": fn, "size": os.path.getsize(fp),
                        "modified": datetime.fromtimestamp(os.path.getmtime(fp)).strftime("%H:%M")
                    })
            resp = {"tasks": tasks, "count": len(tasks)}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(resp, ensure_ascii=False).encode())
        elif self.path.startswith("/get?id="):
            task_id = self.path.split("?id=", 1)[1]
            fp = os.path.join(INBOX_DIR, task_id)
            if os.path.exists(fp):
                with open(fp) as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(content.encode())
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b'not found')
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/add":
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len).decode()
            try:
                data = json.loads(body)
                content = data.get("content", "")
                ts = datetime.now().strftime("%Y%m%d%H%M%S")
                fn = f"TASK-MANUAL-{ts}.md"
                fp = os.path.join(INBOX_DIR, fn)
                with open(fp, "w") as f:
                    f.write(f"# {content}\n\n")
                    f.write(f"**创建时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "id": fn}).encode())
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
        elif self.path == "/snapshot" and self.command == "POST":
            try:
                result = subprocess.run(
                    ["node", "/home/admin/openclaw/workspace/scripts/snapshot.js"],
                    capture_output=True, text=True, timeout=30
                )
                resp = {
                    "ok": result.returncode == 0,
                    "stdout": result.stdout.strip(),
                    "stderr": result.stderr.strip()[:200] if result.stderr else ""
                }
                self.send_response(200 if result.returncode == 0 else 500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(resp, ensure_ascii=False).encode())
            except subprocess.TimeoutExpired:
                self.send_response(408)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error":"snapshot timeout"}')
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(str(e).encode())
        else:
            self.send_response(404)
            self.end_headers()

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    allow_reuse_address = True

if __name__ == "__main__":
    print(f"inbox_server 启动，端口 {PORT}")
    with ThreadedHTTPServer(("0.0.0.0", PORT), Handler) as httpd:
        httpd.serve_forever()
