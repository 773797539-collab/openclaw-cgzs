#!/usr/bin/env python3
"""
activity_logger.py - 活动记录（已重构：通知降噪）

重构原则：
- commit 只做内部留痕，不直接逐条推送
- 多个 commit 汇总成 1 条摘要
- 只有"主结果/真失败/真阻塞/待审批"才推送
- HEARTBEAT 类纯心跳不推送

推送规则：
- 聚合时间窗：1小时（只推送1小时内的汇总）
- 单次推送阈值：>=3条commit 或 包含真失败/真阻塞
- 抑制规则：
  * HEARTBEAT_OK / 心跳 / health check → 不推送
  * docs/ / chore: / merge: → 不推送（静默留痕）
  * fix/feat/add/implement + 无失败 → 汇总推送
  * 真失败 / 真阻塞 / 待审批 → 立即推送
- 超过20条自动合并为摘要
"""
import time, os, subprocess
from datetime import datetime, timedelta
from threading import Lock

WORKSPACE = "/home/admin/openclaw/workspace"
LOG_FILE = os.path.join(WORKSPACE, "logs", "activity.log")
BATCH_WINDOW_SECONDS = 3600  # 1小时聚合窗口
NOTIFY_THRESHOLD = 3  # 少于3条不推送（除非有失败/阻塞）
MAX_BATCH = 20  # 超过20条强制摘要

# Mutex for thread safety
_lock = Lock()

# In-memory buffer
_commit_buffer = []  # list of {time, type, msg, sha, category}
_last_notify = 0  # timestamp of last notification

# Categories that are NOISE (never push, just log internally)
NOISE_CATEGORIES = {
    'heartbeat', '心跳', 'health check', 'status update',
    'heartbeat_ok', 'hearthbeat', 'Hearthbeat',
}

# Categories that are SILENT (don't push, don't even log as activity)
SILENT_CATEGORIES = {
    'docs', 'chore', 'merge', 'style', 'refactor', 'typo', 'cleanup',
}

# Commit types that are MEANINGFUL (always potentially push-worthy)
MEANINGFUL_TYPES = {
    'fix', 'feat', 'add', 'implement', 'new', 'create', '建立',
    '新增', '实现', '修复', '建立', '创建',
}

# Commit types that are BLOCKING/FAILING (always push immediately)
ALERT_TYPES = {
    'fail', 'error', 'block', 'broken', 'crash', 'blocked',
    '失败', '错误', '阻塞', '崩溃',
}


def _classify_commit(msg: str) -> str:
    """分类 commit，返回 category name"""
    msg_lower = msg.lower()
    if any(k in msg_lower for k in NOISE_CATEGORIES):
        return 'NOISE'
    if any(k in msg_lower for k in SILENT_CATEGORIES):
        return 'SILENT'
    if any(k in msg_lower for k in ALERT_TYPES):
        return 'ALERT'
    if any(k in msg_lower for k in MEANINGFUL_TYPES):
        return 'MEANINGFUL'
    return 'ROUTINE'


def _should_push() -> bool:
    """判断是否应该推送"""
    if not _commit_buffer:
        return False
    now = time.time()
    # 检查是否超时（超过1小时强制推送一次摘要）
    if now - _last_notify > BATCH_WINDOW_SECONDS:
        return True
    # 检查是否有 ALERT
    if any(c['category'] == 'ALERT' for c in _commit_buffer):
        return True
    # 超过最大批次
    if len(_commit_buffer) >= MAX_BATCH:
        return True
    # 超过阈值且有一定间隔
    if len(_commit_buffer) >= NOTIFY_THRESHOLD and now - _last_notify >= 60:
        return True
    return False


def _format_summary() -> str:
    """格式化推送消息"""
    noise = [c for c in _commit_buffer if c['category'] == 'NOISE']
    silent = [c for c in _commit_buffer if c['category'] == 'SILENT']
    meaningful = [c for c in _commit_buffer if c['category'] == 'MEANINGFUL']
    alerts = [c for c in _commit_buffer if c['category'] == 'ALERT']
    routine = [c for c in _commit_buffer if c['category'] == 'ROUTINE']

    total = len(_commit_buffer)
    ts = datetime.now().strftime("%H:%M")

    lines = [f"📊 Activity Summary [{ts}] ({total}条)"]

    if alerts:
        lines.append(f"🚨 重要: {len(alerts)}条")
        for c in alerts[:3]:
            lines.append(f"  • {c['msg'][:50]}")
        if len(alerts) > 3:
            lines.append(f"  ...还有{len(alerts)-3}条")

    if meaningful:
        lines.append(f"✅ 产出: {len(meaningful)}条")
        for c in meaningful[:5]:
            lines.append(f"  • {c['msg'][:50]}")
        if len(meaningful) > 5:
            lines.append(f"  ...还有{len(meaningful)-5}条")

    if routine:
        lines.append(f"📝 例行: {len(routine)}条")

    if noise or silent:
        hidden = len(noise) + len(silent)
        lines.append(f"(已过滤{hidden}条心跳/杂项)")

    return "\n".join(lines)


def log_commit(sha: str, msg: str):
    """记录一个 commit"""
    category = _classify_commit(msg)
    entry = {
        'time': time.time(),
        'type': category,
        'msg': msg,
        'sha': sha[:8],
        'category': category,
    }

    # Always log to file
    with _lock:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a') as f:
            f.write(f"{datetime.now().isoformat()} [{category}] {sha[:8]} {msg}\n")

        # Only buffer non-SILENT entries
        if category != 'SILENT':
            _commit_buffer.append(entry)
        else:
            # SILENT: just log to file, don't buffer
            pass

    # Check if we should push
    if _should_push():
        _do_notify()


def _do_notify():
    """执行推送"""
    global _last_notify
    with _lock:
        if not _commit_buffer:
            return
        msg = _format_summary()
        _commit_buffer.clear()
        _last_notify = time.time()

    _notify(msg)


def _notify(msg: str):
    """实际发送通知"""
    try:
        import urllib.request, json
        config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'alert_config.json')
        if os.path.exists(config_path):
            with open(config_path) as f:
                config = json.load(f)
            feishu_url = config.get('feishu_webhook') or os.environ.get('FEISHU_WEBHOOK')
            if feishu_url:
                req = urllib.request.Request(feishu_url,
                    data=json.dumps({"msg_type": "text", "content": {"text": msg}}).encode(),
                    headers={"Content-Type": "application/json"})
                urllib.request.urlopen(req, timeout=10)
                return

        # Telegram fallback
        try:
            import telegram
            from ..config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
            bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
            bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)
        except Exception:
            pass
    except Exception:
        pass


def flush():
    """强制推送所有缓冲消息"""
    with _lock:
        if _commit_buffer:
            msg = _format_summary()
            _commit_buffer.clear()
            _last_notify = time.time()
    _notify(msg)


def run_monitor(interval: int = 30):
    """定期检查 commit 并记录（后台运行）"""
    known_commits = set()
    log_path = os.path.join(WORKSPACE, '.git', 'logs', 'HEAD')
    if os.path.exists(log_path):
        r = subprocess.run(['git', 'log', '--format=%H %s', '-n', '50'],
                         cwd=WORKSPACE, capture_output=True, text=True)
        for line in r.stdout.strip().split('\n'):
            if line:
                parts = line.split(' ', 1)
                if len(parts) == 2:
                    known_commits.add(parts[0])

    while True:
        r = subprocess.run(['git', 'log', '--format=%H %s', '-n', '10'],
                          cwd=WORKSPACE, capture_output=True, text=True)
        for line in reversed(r.stdout.strip().split('\n')):
            if line:
                parts = line.split(' ', 1)
                if len(parts) == 2 and parts[0] not in known_commits:
                    sha, msg = parts
                    known_commits.add(sha)
                    log_commit(sha, msg)
        time.sleep(interval)


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--monitor':
        run_monitor()
    else:
        print("activity_logger.py - 活动记录（通知降噪版）")
        print("Usage: python3 activity_logger.py --monitor")
