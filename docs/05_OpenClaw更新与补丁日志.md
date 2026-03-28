# 05_OpenClaw更新与补丁日志.md

**创建**: 2026-03-28
**当前版本**: OpenClaw 2026.3.24 (cff6dc9)

---

## 版本历史

| 版本 | Commit | 日期 | 备注 |
|------|--------|------|------|
| 2026.3.24 | cff6dc9 | 2026-03-26 | 当前运行版本 |
| - | - | 2026-03-26 | 首次部署 stock-assistant |

---

## OpenClaw 已知问题

### 1. wecom-openclaw-plugin 加载失败
- **状态**: 已禁用，不影响主功能
- **原因**: 插件版本不兼容

### 2. exec 工具对 MCP HTTP 82.156.17.205 返回 HTTP 501
- **状态**: 已修复
- **方案**: 使用 urllib 直接调用 MCP HTTP API，不通过 exec subprocess
- **关键发现**: subprocess curl 对 MCP 返回 501，urllib 正常

### 3. MCP SSE 响应格式
- **格式**: `event: message\r\ndata: {...}`
- **解析**: 需找到 `data:` 后的 JSON

---

## OpenClaw 配置

| 项目 | 值 |
|------|-----|
| 版本 | 2026.3.24 (cff6dc9) |
| Node | v24.14.0 |
| 工作区 | /home/admin/openclaw/workspace |
| Cron | 6 个任务注册 |
| Feishu | 已集成 |

---

## 插件列表

| 插件 | 状态 |
|------|------|
| feishu_doc | ✅ 正常 |
| feishu_chat | ✅ 正常 |
| feishu_wiki | ✅ 正常 |
| feishu_drive | ✅ 正常 |
| feishu_bitable | ✅ 正常 |
| DingTalk | ✅ 正常 |
| wecom-openclaw-plugin | ❌ 已禁用 |

---

## CLI 参考

```bash
# 版本
openclaw --version

# Gateway
openclaw gateway status/start/stop/restart

# Cron
openclaw cron list
openclaw cron run <id>

# Message
openclaw message send --channel feishu --target <open_id> --message <text>
```
