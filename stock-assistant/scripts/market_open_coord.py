#!/usr/bin/env python3
"""
每日开盘扫描协调脚本
cron 触发 → 交易日中执行 market_open_scan → 发飞书通知
"""
import sys
import subprocess
from pathlib import Path

WORKSPACE = Path("/home/admin/openclaw/workspace")
SYS_CRONTAB = "/tmp/market_open_cron.sh"

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
    """确保系统 crontab 有开盘扫描任务"""
    cron_entry = "0 9 * * 1-5 cd /home/admin/openclaw/workspace && python3 stock-assistant/scripts/market_open_coord.py >> logs/market-open.log 2>&1\n"
    try:
        existing = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        if "market_open_coord" not in existing.stdout:
            new_crontab = existing.stdout + cron_entry
            subprocess.run(["crontab", "-"], input=new_crontab, text=True)
            print(f"[coord] crontab 注册成功")
        else:
            print(f"[coord] crontab 已存在，跳过")
    except Exception as e:
        print(f"[coord] crontab 注册失败: {e}")

def main():
    print(f"[{__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开盘协调脚本启动")
    
    if not is_trading_day():
        print(f"[coord] 非交易日，跳过")
        return
    
    ensure_cron()
    
    # 执行开盘扫描
    scan_script = WORKSPACE / "stock-assistant" / "scripts" / "market_open_scan.py"
    if scan_script.exists():
        print(f"[coord] 执行开盘扫描...")
        result = subprocess.run(["python3", str(scan_script)], 
                               capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            print(f"[coord] 开盘扫描完成")
            if result.stdout:
                print(result.stdout[:500])
        else:
            print(f"[coord] 扫描失败: {result.stderr[:200]}")
    else:
        print(f"[coord] 扫描脚本不存在: {scan_script}")

if __name__ == "__main__":
    main()
