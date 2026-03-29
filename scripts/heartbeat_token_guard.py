#!/usr/bin/env python3
"""
heartbeat_token_guard.py - Token 检查守卫
每次 heartbeat 开头调用，返回 True 则继续，返回 False 则静默停摆

用法（在 heartbeat 开头调用）：
    from heartbeat_token_guard import check_token
    if not check_token():
        print("HEARTBEAT_OK")  # 静默停摆，不发任何消息
        exit(0)
"""
import subprocess
import sys
import json
from pathlib import Path

API_KEY = "sk-cp-B-h-RjQvCGBUCL42doqN1zKJMqhUx1McK-23ceE0nk7WAkHVzqby80U9S2TL6fjQUTolm7aobtX9squzXW5Vsoc-mUYK32RS9ohNwmruEg6vcfU0TjPjTi0"

def get_token_status():
    """返回 (remaining, total, percentage, hours_left)"""
    try:
        result = subprocess.run([
            "curl", "-s",
            "https://www.minimaxi.com/v1/api/openplatform/coding_plan/remains",
            "-H", f"Authorization: Bearer {API_KEY}",
            "-H", "Content-Type: application/json"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            return None  # API 失败
        
        data = json.loads(result.stdout)
        if data.get("base_resp", {}).get("status_code") != 0:
            return None  # API 错误
        
        for m in data.get("model_remains", []):
            if "MiniMax-M*" in m.get("model_name", ""):
                remaining = m["current_interval_usage_count"]
                total = m["current_interval_total_count"]
                hours_left = m["remains_time"] / 1000 / 3600
                return remaining, total, remaining / total, hours_left
        
        return None  # 未找到主模型
    except Exception:
        return None

def check_token():
    """
    检查 Token 状态。
    返回 True = 可以继续工作
    返回 False = 静默停摆（不发任何消息）
    """
    status = get_token_status()
    
    if status is None:
        # API 失败，静默停摆
        print("[Token Guard] API失败，静默停摆", flush=True)
        return False
    
    remaining, total, pct, hours = status
    
    if remaining == 0:
        print(f"[Token Guard] Token=0，静默停摆", flush=True)
        return False
    
    # 剩余 > 0，继续工作
    print(f"[Token Guard] 剩余 {remaining}/{total} ({pct*100:.1f}%)，约{hours:.1f}h，继续", flush=True)
    return True

if __name__ == "__main__":
    if check_token():
        sys.exit(0)  # 可以继续
    else:
        sys.exit(1)  # 静默停摆
