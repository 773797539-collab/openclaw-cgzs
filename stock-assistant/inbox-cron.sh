#!/bin/bash
# inbox-cron.sh - v1.2.5 灰度实施版
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INBOX_DIR="$SCRIPT_DIR/tasks/inbox"
TODO_DIR="$SCRIPT_DIR/tasks/todo"
DOING_DIR="$SCRIPT_DIR/tasks/doing"
DONE_DIR="$SCRIPT_DIR/tasks/done"
FAILED_DIR="$SCRIPT_DIR/tasks/failed"
DUPLICATES_DIR="$SCRIPT_DIR/tasks/failed/duplicates"

LOGFILE="/tmp/inbox-cron.log"
PIDFILE="/tmp/inbox-cron.pid"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') [$$] $*" >> "$LOGFILE"; }

# Log rotation
if [ -f "$LOGFILE" ] && [ "$(wc -l < "$LOGFILE")" -gt 1000 ]; then
    tail -n 500 "$LOGFILE" > "${LOGFILE}.tmp" && mv "${LOGFILE}.tmp" "$LOGFILE"
fi

# PID 锁
if [ -f "$PIDFILE" ]; then
    OLD=$(cat "$PIDFILE")
    [ -d "/proc/$OLD" ] && { log "PID $OLD 运行中，跳过"; exit 0; }
fi
echo $$ > "$PIDFILE"
trap 'rm -f "$PIDFILE"' EXIT

log "inbox-cron v1.2.5 启动"
mkdir -p "$INBOX_DIR" "$TODO_DIR" "$DOING_DIR" "$DONE_DIR" "$FAILED_DIR" "$DUPLICATES_DIR"

timestamp="$(date '+%Y%m%d%H%M%S')"
processed=0; failed=0; duplicates=0

# ===== 重复检测 =====
is_duplicate() {
    local id="$1"
    [ -f "$TODO_DIR/${id}.md" ] && return 0
    [ -f "$DOING_DIR/${id}.running" ] && return 0
    return 1
}

# ===== 扫描 inbox/ =====
if [ -f "$(echo "$INBOX_DIR"/*.md 2>/dev/null)" ] 2>/dev/null; then
    for file in "$INBOX_DIR"/*.md; do
        [ -f "$file" ] || continue
        filename="$(basename "$file")"
        id="$(echo "$filename" | sed 's/^TASK-//;s/\.md$//')"

        # 重复检测
        if is_duplicate "$id"; then
            if mv "$file" "$DUPLICATES_DIR/${id}-${timestamp}.failed" 2>/dev/null; then
                log "重复隔离(mv成功): $id"
            elif cp "$file" "$DUPLICATES_DIR/${id}-${timestamp}.failed" 2>/dev/null; then
                rm -f "$file"; log "重复隔离(mv失败,cp成功): $id"
            else
                [ -f "$file" ] && mv "$file" "${file}.DUPLICATE_UNHANDLED.${timestamp}" 2>/dev/null
                log "重复隔离失败，保留待人工: $id"
            fi
            duplicates=$((duplicates+1)); continue
        fi

        # 正常入队
        if mv "$file" "$TODO_DIR/${id}.md" 2>/dev/null; then
            log "入队: $id → $TODO_DIR/"
            processed=$((processed+1))
        else
            if cp "$file" "$FAILED_DIR/${id}-${timestamp}.failed" 2>/dev/null; then
                rm -f "$file"; log "mv失败，已copy到failed: $id"
            else
                [ -f "$file" ] && mv "$file" "${file}.HANDLING_REQUIRED.${timestamp}" 2>/dev/null
                log "mv+cp均失败，保留原位待人工: $id"
            fi
            failed=$((failed+1))
        fi
    done
else
    log "inbox 空"
fi

# ===== inbox-disp.js 派发 =====
INBOX_DISP="$SCRIPT_DIR/../scripts/inbox-disp.js"
if [ -x "$(command -v node)" ] && [ -f "$INBOX_DISP" ]; then
    result=$(node "$INBOX_DISP" 2>/dev/null)
    [ -n "$result" ] && log "inbox-disp: $result"
fi

log "完成: processed=$processed failed=$failed duplicates=$duplicates"
rm -f "$PIDFILE"
