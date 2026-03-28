#!/usr/bin/env python3
"""
cron_health_check.py - cron 任务健康检查
验证所有注册 cron 的状态和下一次触发时间
"""
import subprocess, json, re
from datetime import datetime

def get_cron_status():
    """从 openclaw cron list 获取状态（按列位置解析）"""
    r = subprocess.run(['openclaw', 'cron', 'list'], capture_output=True, text=True, timeout=10)
    lines = r.stdout.strip().split('\n')
    crons = []
    for line in lines:
        if not line.strip() or line.startswith('[plugins]') or line.startswith('ID '):
            continue
        # 按表头列位置解析: ID(0-37) Name(37-62) Schedule(62-95) Next(95-106) Last(106-117) Status(117-127)
        cron_id = line[0:37].strip()
        name = line[37:62].strip()
        schedule = line[62:95].strip()
        next_run = line[95:106].strip()
        last_run = line[106:117].strip()
        status = line[117:127].strip()
        if cron_id:
            crons.append({
                'id': cron_id,
                'name': name,
                'schedule': schedule,
                'next': next_run,
                'last': last_run,
                'status': status,
            })
    return crons

def check_alert_log():
    """检查止损告警日志"""
    import os
    LOG_PATH = '/home/admin/openclaw/workspace/stock-assistant/data/alert_log.json'
    if not os.path.exists(LOG_PATH):
        return None
    with open(LOG_PATH) as f:
        d = json.load(f)
    last = d.get('last_check', 'N/A')
    alerts = d.get('alerts', [])
    return {'last_check': last, 'alert_count': len(alerts), 'active_alerts': alerts}

def check_portal():
    """检查 Portal 状态"""
    import urllib.request
    try:
        with urllib.request.urlopen('http://localhost:8081/api/status/all', timeout=3) as r:
            d = json.loads(r.read())
        g = d.get('governance', {})
        return {'agent_count': g.get('agent_count', '?'), 'status': 'ok'}
    except:
        return {'status': 'DOWN'}

if __name__ == '__main__':
    import sys
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    as_json = '--json' in sys.argv or '-j' in sys.argv

    crons = get_cron_status()
    alert = check_alert_log()
    portal = check_portal()

    if as_json:
        import json
        output = {
            'timestamp': now,
            'crons': crons,
            'alert': alert,
            'portal': portal,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(f'# Cron 健康检查 - {now}')
        print()
        print(f'## Cron 任务 ({len(crons)}个)')
        for c in crons:
            emoji = '✅' if c['status'] == 'ok' else '⏸️' if c['status'] == 'idle' else '⚠️'
            print(f'{emoji} [{c["status"]}] {c["name"]} | schedule={c["schedule"]} | next={c["next"]} | last={c["last"]}')
        print()

        if alert:
            print(f'## 止损日志 | last_check={alert["last_check"]} | alerts={alert["alert_count"]}')
        print()

        print(f'## Portal | status={portal["status"]}' + (f' | agents={portal["agent_count"]}' if portal.get("agent_count") else ''))
        print()

        weekday = datetime.now().weekday()
        if weekday >= 5:
            print('⚠️ 今日是周末，大部分 cron 不运行。下一次工作日运行：周一 00:30（止损监控）')
