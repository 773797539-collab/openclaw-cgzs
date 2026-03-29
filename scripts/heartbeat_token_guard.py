#!/usr/bin/env python3
"""
heartbeat_token_guard.py
Token 检查守卫：查询 MiniMax Token 剩余量，决定是否继续 heartbeat。
规则：
- API 成功 + remaining > 0 → 返回 True，继续工作
- API 成功 + remaining = 0 → 返回 False，停止
- API 失败（网络/超时/解析错误）→ 重试 3 次，每次等 3 秒
- 3 次全失败 → 写 error log，但返回 True（网络问题时不过度保守，静默降级但继续工作）
"""
import subprocess
import json
import time
import sys
import os

API_KEY = "sk-cp-B-h-RjQvCGBUCL42doqN1zKJMqhUx1McK-23ceE0nk7WAkHVzqby80U9S2TL6fjQUTolm7aobtX9squzXW5Vsoc-mUYK32RS9ohNwmruEg6vcfU0TjPjTi0"
API_URL = "https://www.minimaxi.com/v1/api/openplatform/coding_plan/remains"
MAX_RETRIES = 3
RETRY_DELAY = 3  # 秒

WORKSPACE = "/home/admin/openclaw/workspace"
LOGFILE = "/tmp/token_guard.log"

def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[token_guard {ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOGFILE, "a") as f:
            f.write(line + "\n")
    except:
        pass

def check_token_once():
    """单次查询 Token，返回 (success, remaining_or_none, error_msg_or_none)"""
    try:
        r = subprocess.run(
            [
                "curl", "-s", "--max-time", "10",
                API_URL,
                "-H", f"Authorization: Bearer {API_KEY}",
                "-H", "Content-Type: application/json"
            ],
            capture_output=True, text=True, timeout=15
        )
        if r.returncode != 0:
            return False, None, f"curl exit={r.returncode}"
        if not r.stdout.strip():
            return False, None, "empty response"
        data = json.loads(r.stdout)
        for m in data.get("model_remains", []):
            if "MiniMax-M*" in m.get("model_name", ""):
                remaining = m["current_interval_usage_count"]  # 字段名含usage，实际=剩余
                total = m["current_interval_total_count"]
                return True, remaining, None
        return False, None, "MiniMax-M* model not found in response"
    except subprocess.TimeoutExpired:
        return False, None, "curl timeout"
    except json.JSONDecodeError as e:
        return False, None, f"JSON parse error: {e}"
    except Exception as e:
        return False, None, f"unexpected error: {e}"

def check_token_with_retry():
    """带重试的 Token 检查"""
    for attempt in range(1, MAX_RETRIES + 1):
        success, remaining, err = check_token_once()
        if success:
            return True, remaining, None
        log(f"API 查询失败（尝试 {attempt}/{MAX_RETRIES}）: {err}")
        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY)
    
    # 3 次全失败：网络问题，不返回 0 停摆
    log(f"API 3次全失败，网络问题，降级处理（返回True继续工作）")
    return False, None, "3次API失败"

def main():
    log("开始检查 Token")
    ok, remaining, err = check_token_with_retry()
    
    if err and not ok:
        # 3次API失败，网络问题 → 降级，继续工作
        print("TOKEN_CHECK: NETWORK_ERROR (降级继续)", flush=True)
        log(f"Token检查降级: {err}，建议继续工作")
        sys.exit(0)  # 静默但继续
    
    if remaining is None:
        print("TOKEN_CHECK: ERROR", flush=True)
        log(f"Token检查异常: {err}")
        sys.exit(1)
    
    total = 4500  # 固定总额度
    used = total - remaining
    used_pct = used / total * 100
    remaining_pct = remaining / total * 100
    
    log(f"Token: {remaining}/{total} ({remaining_pct:.1f}%), 已用 {used}/{total} ({used_pct:.1f}%)")
    
    if remaining <= 0:
        print(f"TOKEN_CHECK: STOP (remaining=0)", flush=True)
        log("Token=0，停止")
        sys.exit(0)  # 静默停止
    else:
        print(f"TOKEN_CHECK: OK remaining={remaining} total={total}", flush=True)
        sys.exit(0)  # 继续

if __name__ == "__main__":
    main()
