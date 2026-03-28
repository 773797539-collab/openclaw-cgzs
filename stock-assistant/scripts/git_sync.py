#!/usr/bin/env python3
"""GitHub Sync 脚本 - 通过 API 同步代码（解决 git push 超时问题）

使用方法:
    python3 git_sync.py [--commit "message"]

依赖: 无（仅用标准库 urllib）
"""
import urllib.request, urllib.error, json, base64, os, sys, subprocess

TOKEN_FILE = os.path.expanduser("~/.config/openclaw/github_token")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
if not TOKEN and os.path.exists(TOKEN_FILE):
    with open(TOKEN_FILE) as f:
        TOKEN = f.read().strip()

REPO = "773797539-collab/openclaw-cgzs"
API = f"https://api.github.com/repos/{REPO}"
BRANCH = "main"
WORKSPACE = "/home/admin/openclaw/workspace"


def gh(method, path, data=None):
    url = API + path
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    if data:
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps(data).encode()
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read()), r.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read()), e.code


def main():
    import subprocess

    # Get workspace git SHA
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=WORKSPACE, capture_output=True, text=True
    )
    local_sha = result.stdout.strip()
    print(f"Local HEAD: {local_sha[:8]}")

    # Get GitHub HEAD
    _, s = gh("GET", "/git/refs/heads/main")
    github_sha = _['object']['sha']
    print(f"GitHub main: {github_sha[:8]}")

    if local_sha == github_sha:
        print("✅ Already synced")
        return

    # Get GitHub tree
    commit_data, _ = gh("GET", f"/git/commits/{github_sha}")
    tree_sha = commit_data['tree']['sha']

    # Collect all files
    skip_dirs = {'.git', 'node_modules', '__pycache__', '.venv'}
    skip_exts = {'.png', '.jpg', '.jpeg', '.gif', '.mp4', '.zip', '.tar', '.gz', '.pdf'}
    max_size = 500_000

    files = []
    for root, dirs, filenames in os.walk(WORKSPACE):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for f in filenames:
            fp = os.path.join(root, f)
            fp_rel = os.path.relpath(fp, WORKSPACE)
            if any(fp_rel.endswith(e) for e in skip_exts):
                continue
            size = os.path.getsize(fp)
            if size > max_size:
                continue
            with open(fp, 'rb') as fh:
                content = fh.read()
            encoded = base64.b64encode(content).decode().replace('\n', '')
            files.append({'path': fp_rel, 'content': encoded})

    print(f"Syncing {len(files)} files...")

    # Create blobs
    tree_items = []
    for i, f in enumerate(files):
        blob_data, status = gh("POST", "/git/blobs", {
            "content": f['content'], "encoding": "base64"
        })
        if status in (201, 200):
            tree_items.append({
                "path": f['path'], "mode": "100644", "type": "blob", "sha": blob_data['sha']
            })
        if (i+1) % 30 == 0:
            print(f"  Blob {i+1}/{len(files)}...")

    # Create tree
    tree_data, ts = gh("POST", "/git/trees", {"base_tree": tree_sha, "tree": tree_items})

    # Create commit
    msg = sys.argv[1] if len(sys.argv) > 1 else f"chore: sync from workspace {local_sha[:8]}"
    commit_data, cs = gh("POST", "/git/commits", {
        "message": msg, "tree": tree_data['sha'], "parents": [github_sha]
    })

    if cs == 201:
        ref_data, rs = gh("PATCH", "/git/refs/heads/main", {
            "sha": commit_data['sha'], "force": False
        })
        print(f"✅ Synced! https://github.com/{REPO}")
    else:
        print(f"❌ Failed: {commit_data}")


if __name__ == "__main__":
    main()
