#!/usr/bin/env python3
"""
每日收盘扫描协调脚本
cron 触发 → 交易日中执行 market_close_scan → 发飞书通知
"""
import sys
import subprocess
from pathlib import Path

WORKSPACE = Path("/home/admin/openclaw/workspace")

def is_trading_day():
    """检查是否为美股交易日"""
    try:
        result = subprocess.run(
            ["python3", "-c", 
             "import datetime; d=datetime.date.today(); print('Y' if d.weekday()<5 else 'N')"],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip() == "Y"
    except:
        return False

def ensure_cron():
    """确保系统 crontab 有收盘扫描任务"""
    cron_entry = "0 16 * * 1-5 cd /home/admin/openclaw/workspace && python3 stock-assistant/scripts/market_close_coord.py >> logs/market-close.log 2>&1\n"
    try:
        existing = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        if "market_close_coord" not in existing.stdout:
            new_crontab = existing.stdout + cron_entry
            subprocess.run(["crontab", "-"], input=new_crontab, text=True)
            print(f"[coord] crontab 注册成功")
        else:
            print(f"[coord] crontab 已存在，跳过")
    except Exception as e:
        print(f"[coord] crontab 注册失败: {e}")

def run_close_scan():
    """执行收盘扫描脚本"""
    scan_script = WORKSPACE / "stock-assistant" / "scripts" / "market_close_scan.py"
    if not scan_script.exists():
        print(f"[coord] 扫描脚本不存在: {scan_script}")
        return False
    
    result = subprocess.run(["python3", str(scan_script)],
                          capture_output=True, text=True, timeout=180)
    if result.returncode == 0:
        print(f"[coord] 收盘扫描完成")
        return True
    else:
        print(f"[coord] 扫描失败: {result.stderr[:200]}")
        return False

def main():
    print(f"[{__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 收盘协调脚本启动")
    
    if not is_trading_day():
        print(f"[coord] 非交易日，跳过")
        return
    
    ensure_cron()
    
    if run_close_scan():
        print(f"[coord] 收盘流程完成")
    else:
        print(f"[coord] 收盘流程异常")

if __name__ == "__main__":
    main()
