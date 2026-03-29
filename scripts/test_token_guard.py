#!/usr/bin/env python3
"""token_guard 测试脚本"""
import sys
sys.path.insert(0, '/home/admin/openclaw/workspace/scripts')
from heartbeat_token_guard import check_token, get_token_status

print("=== Token Guard 测试 ===\n")

# 测试1：get_token_status
print("测试 get_token_status():")
status = get_token_status()
if status is None:
    print("  ❌ 返回 None（API失败）")
else:
    remaining, total, pct, hours = status
    print(f"  ✅ remaining={remaining}, total={total}")
    print(f"     剩余 {pct*100:.1f}%，约 {hours:.1f}h")

print()

# 测试2：check_token
print("测试 check_token():")
ok = check_token()
print(f"  {'✅ 可以继续' if ok else '❌ 静默停摆'}")
