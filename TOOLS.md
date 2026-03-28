# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

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
curl --location 'https://www.minimaxi.com/v1/api/openplatform/coding_plan/remains' \
--header 'Authorization: Bearer <API Key>' \
--header 'Content-Type: application/json'
```

### 字段含义（容易搞错）
| 字段 | 意思 | 示例值 |
|------|------|--------|
| `current_interval_total_count` | 当前周期**总**额度 | 4500 |
| `current_interval_usage_count` | 当前周期**剩余**次数（⚠️ 当前实测映射：字段值=剩余，与官方后台一致，字段名含usage但实测不符，待官方确认 | 4192 |
| `remains_time` | 当前周期**剩余时间**（毫秒） | 9004868 ≈ 2.5小时 |
| `current_weekly_total_count` | 本周总额度 | 0 |
| `current_weekly_usage_count` | 本周已用 | 0 |
| `weekly_remains_time` | 本周剩余时间（毫秒） | 336604868 ≈ 3.9天 |

**⚠️ 停止线判断规则（2026-03-27 V2 纠正）**：
- `current_interval_usage_count` = **剩余额度**（⚠️ 当前实测映射：字段值=剩余，与官方后台一致，字段名含usage但实测不符，待官方确认）
- 已用 = `total_count - usage_count`
- 停止条件：剩余 ≤ 20% 时停止（即 `usage_count <= total * 0.2` 时停止）
- 当前主模型（23:21）：剩余 366/4500（8.1%），已用 4134/4500（91.9%）→ ⚠️ 已触发停止线
- 汇报模板：必须同时写"剩余X/Y(Z%)"和"已用A/B(C%)"，禁止只写"X/Y"
- 自检公式：已用% + 剩余% = 100%（验证：6.8%+93.2%=100% ✅）

**主模型（MiniMax-M*）当前状态（22:17）**：
| 指标 | 值 | 比例 |
|------|----|------|
| 剩余（字段usage） | 4192 | 93.2% |
| 已用（推算） | 308 | 6.8% |
| 官方后台剩余 | 4192 | 93.2% ✅ |
| 官方后台已用 | 308 | 6.8% ✅ |

| 已用 | 4205 | 93.4% |
| 剩余 | 295 | 6.6% |
| 剩余时间 | ~1.9小时 | - |

### 用户信息
- 手机号：15279089857
- API Key：<MINIMAX_API_KEY_REVOKED>（已记录）


## 🚀 Token-Flush 模式（2026-03-27 22:41 激活）
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
