# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

## MiniMax Coding Plan 用量查询

### API 命令
```bash
curl -s 'https://www.minimaxi.com/v1/api/openplatform/coding_plan/remains' \
  -H 'Authorization: Bearer sk-cp-B-h-RjQvCGBUCL42doqN1zKJMqhUx1McK-23ceE0nk7WAkHVzqby80U9S2TL6fjQUTolm7aobtX9squzXW5Vsoc-mUYK32RS9ohNwmruEg6vcfU0TjPjTi0' \
  -H 'Content-Type: application/json'
```

### 字段含义
| 字段 | 意思 | 示例值 |
|------|------|--------|
| `current_interval_total_count` | 当前周期**总**额度 | 4500 |
| `current_interval_usage_count` | 当前周期**剩余**次数（字段名含usage但语义=剩余，与官方后台一致） | 4192 |
| `remains_time` | 当前周期**剩余时间**（毫秒） | 9004868 ≈ 2.5小时 |
| `current_weekly_total_count` | 本周总额度 | 0 |
| `current_weekly_usage_count` | 本周已用 | 0 |

**⚠️ 停止线判断规则**：
- `current_interval_usage_count` = **剩余额度**（字段名含usage但语义是剩余，与官方后台一致）
- 已用 = `total_count - usage_count`
- 停止条件：剩余 ≤ 20% 时进入关注（`usage_count <= total * 0.2`）
- Token-Flush：剩余 > 0 时持续工作，不主动停止
- 汇报模板：必须同时写"剩余X/Y(Z%)"和"已用A/B(C%)"
- 自检公式：已用% + 剩余% = 100%

### 用户信息
- 手机号：15279089857
- API Key：sk-cp-B-h-RjQvCGBUCL42doqN1zKJMqhUx1McK-23ceE0nk7WAkHVzqby80U9S2TL6fjQUTolm7aobtX9squzXW5Vsoc-mUYK32RS9ohNwmruEg6vcfU0TjPjTi0

### Token 查询脚本
```python
import subprocess, json
result = subprocess.run([
    "curl", "-s",
    "https://www.minimaxi.com/v1/api/openplatform/coding_plan/remains",
    "-H", "Authorization: Bearer sk-cp-B-h-RjQvCGBUCL42doqN1zKJMqhUx1McK-23ceE0nk7WAkHVzqby80U9S2TL6fjQUTolm7aobtX9squzXW5Vsoc-mUYK32RS9ohNwmruEg6vcfU0TjPjTi0",
    "-H", "Content-Type: application/json"
], capture_output=True, text=True)
data = json.loads(result.stdout)
for m in data.get("model_remains", []):
    if "MiniMax-M*" in m.get("model_name", ""):
        A = m["current_interval_usage_count"]  # 剩余
        B = m["current_interval_total_count"]
        print(f"剩余 {A}/{B} ({A/B*100:.1f}%)，已用 {B-A}/{B} ({(B-A)/B*100:.1f}%)")
```

## 🚀 Token-Flush 模式
**规则**：剩余>0就不停止。禁止HEARTBEAT_OK（剩余>0时）。内部任务池持续运转。

## OpenClaw 环境信息

- 版本：OpenClaw 2026.3.24 (cff6dc9)
- Node：v24.14.0
- 工作区：/home/admin/openclaw/workspace

## 项目目录结构

已按实施总文档 v2.2 初始化：

```
workspace/
├── docs/
│   ├── 实施总文档_v2.2.md  ← 主文档
│   ├── changelog/project-change-log.md  ← 变更记录
│   ├── decisions/
│   └── failure-cases/
├── memory/
├── tasks/
│   ├── todo/
│   ├── doing/
│   ├── done/
│   ├── blocked/
│   └── approval/
├── reports/
├── runtime/traces/
├── logs/
├── data/
├── exports/
└── avatars/
```

Add whatever helps you do your job. This is your cheat sheet.
