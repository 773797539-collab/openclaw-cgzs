# 环境基线记录 - 2026-03-26

**记录时间**: 2026-03-26 02:40 GMT+8
**OpenClaw 版本**: 2026.3.24 (cff6dc9)
**Node**: v24.14.0
**工作区**: /home/admin/openclaw/workspace

---

## 一、当前服务状态

| 组件 | 状态 | 说明 |
|------|------|------|
| Gateway | ✅ 运行中 (pid 7193) | loopback:18789 |
| RPC | ✅ ok | 正常 |
| Feishu 频道 | ✅ 已配置 | appId: cli_a94e9c41cd78dcc8 |
| 主 Agent | ✅ main | 模型: MiniMax-M2.7 |

---

## 二、已知问题

### 问题1: wecom-openclaw-plugin 加载失败
- **现象**: Plugin id mismatch (config uses "wecom-openclaw-plugin", export uses "wecom")
- **影响**: 插件无法加载，但不影响主链路
- **风险等级**: 低
- **是否阻塞**: 否（不影响主业务）
- **处理方式**: 记录，继续推进

---

## 三、配置摘要

### 模型配置
- 主模型: MiniMax-M2.7 (model_1774461627132)
- API Key: <MINIMAX_API_KEY>
- 上下文窗口: 128000
- 最大输出: 4096

### Gateway 配置
- 端口: 18789
- 模式: local (loopback)
- 认证: token 模式
- Tailscale: off

### 插件状态
| 插件 | 状态 |
|------|------|
| qqbot | ✅ 已安装 |
| dingtalk-connector | ✅ 已安装 |
| wecom-openclaw-plugin | ❌ 加载失败 |
| feishu | ✅ 已启用 |
| minimax | ✅ 已启用 |

---

## 四、工作区现状

```
/home/admin/openclaw/workspace/
├── docs/
│   ├── 实施总文档_v2.2.md
│   ├── changelog/
│   │   ├── project-change-log.md
│   │   └── night-session-2026-03-26.md
│   ├── decisions/
│   └── failure-cases/
├── memory/
├── tasks/todo, doing, done, blocked, approval/
├── reports/
├── runtime/traces/
├── logs/
├── data/
├── exports/
└── avatars/robot-avatar.jpeg
```

---

## 五、Git 状态

- 未配置用户身份
- 存在未提交的变更（目录结构和文档导入）
- 需用户提供 name 和 email 后才能提交

---

## 六、下一步

进入阶段1：备份与恢复底座
