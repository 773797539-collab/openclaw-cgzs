# 目录结构与数据契约

**版本**: v2.0
**更新**: 2026-03-28
**依据**: 实施总文档 v2.2 第十章

---

## 一、实际目录结构

```
/home/admin/openclaw/workspace/
├── AGENTS.md              # AI Agent 核心规则
├── HEARTBEAT.md          # 心跳监控配置
├── MEMORY.md             # 长期记忆
├── USER.md               # 用户信息
├── IDENTITY.md           # AI 身份
├── SOUL.md               # AI 人格
├── TOOLS.md              # 本地工具备注
├── BOOTSTRAP.md          # 初始引导
│
├── avatar/               # 头像文件
├── backups/              # 备份归档
├── data/                 # 共享数据文件
├── docs/                 # 文档目录
│   ├── 实施总文档_v2.2.md
│   ├── 01_当前环境与版本清单.md
│   ├── 02_已验证有效命令与流程.md
│   ├── 03_踩坑记录与失败样本.md
│   ├── 04_验收闭环示例.md
│   ├── CRON_CONFIG.md
│   ├── directory-structure.md  # 本文件
│   └── ...
├── exports/              # 导出文件（DOCX等）
├── logs/                 # 日志文件
├── memory/               # 每日记忆
├── portal/               # 统一门户外壳
│   ├── index.md          # 门户源码
│   ├── index.html        # 生成后的静态页
│   ├── build_index.py    # 生成脚本
│   ├── server.py         # Portal 服务
│   └── status/           # 实时状态
│       ├── system.json
│       ├── portfolio.json
│       ├── portfolio_history.json
│       └── tasks.json
├── reports/              # 导出报告（不git追踪）
├── runtime/              # 运行态数据
│   └── traces/
├── scripts/               # 共享脚本
├── stock-assistant/      # 股票辅助项目
│   ├── scripts/          # 业务脚本
│   ├── reports/          # 报告输出
│   ├── data/             # 项目数据文件
│   ├── tasks/            # 项目任务池
│   └── memory/            # 项目记忆
└── tasks/                # 全局任务池
    ├── todo/
    ├── doing/
    ├── done/
    └── blocked/
```

---

## 二、关键数据契约

| 文件 | 用途 | 格式 |
|------|------|------|
| `portal/status/portfolio.json` | 持仓快照 | JSON，含 holdings/summary |
| `portal/status/portfolio_history.json` | 持仓历史 | JSON，含 records |
| `portal/status/tasks.json` | 任务池 | JSON，含 doing/todo/done |
| `portal/status/system.json` | 系统状态 | JSON，含 git commit / lastUpdated |
| `stock-assistant/data/watchlist.yaml` | 自选股配置 | YAML，含持仓成本 |
| `stock-assistant/data/alert_config.json` | 止损配置 | JSON |
| `stock-assistant/data/alert_log.json` | 告警日志 | JSON |
| `stock-assistant/data/stock_pool.json` | 候选股池 | JSON，含候选股列表 |

---

## 三、脚本入口规范

所有脚本必须满足：
- 有 `if __name__ == "__main__":` 入口
- 有 `is_trading_day()` 或 `can_run()` 非交易日保护
- 使用 `urllib` 而非 `subprocess curl` 调用 MCP HTTP
- 日志输出含时间戳
