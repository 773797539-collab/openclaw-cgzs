# 迁移方案：从不适合常驻的环境 → systemd 托管环境

**生成时间**：2026-03-30
**目标**：让 inbox-cron 和 task_executor 真正常驻后台，开机自启，日志留存

---

## 一、迁移目标

**当前环境为什么不适合真后台常驻**

| 问题 | 原因 | 后果 |
|------|------|------|
| cron daemon 死亡无法重启 | `sudo systemctl start cron` 需要 root 密码 | inbox-cron 无法被 crontab 唤醒 |
| nohup/setsid 后台进程被 SIGTERM | `inbox-cron.sh` 的 `trap 'rm -f "$PIDFILE"' EXIT` | daemon 每次执行完都被 kill |
| 没有进程管理器 | 进程崩溃后无法自动拉起 | 一次性运行可以，持续运行不行 |
| 磁盘日志无处写 | `/tmp` 会被清理 | 日志丢失 |

**核心矛盾**：
- inbox-cron.sh 用 `trap EXIT` 清理 PID 文件，这让它成为一个"一次性脚本"而非"常驻服务"
- 它的设计是"每次 cron 触发 → 启动 → 执行 → 退出"，不是"启动后持续运行等待下次触发"

---

## 二、目标环境最小要求

### 必要条件（必须满足）

1. **systemd 可用**
   - `systemctl --user` 可执行（需要 user session）
   - 当前环境已有：`~/.config/systemd/user/openclaw-gateway.service` 已存在
   - 说明 systemd user session 可用

2. **cron daemon 可用且自启动**
   - `sudo systemctl start crond` 能成功
   - 或者 crontab 的 `*/5 * * * *` 能被系统 cron 执行

3. **进程能够真正后台常驻**
   - 不被 SIGTERM kill
   - 不依赖控制终端（tty）

4. **日志文件持久化**
   - `~/logs/` 或 `/var/log/` 可写
   - 日志文件不依赖 `/tmp`

5. **能够设置开机自启**
   - `systemctl --user enable` 可用
   - 或者 `@reboot` 在 crontab 中可用

### 目标环境配置

```bash
# 1. systemd user 服务：inbox-cron.service
[Unit]
Description=OpenClaw Inbox Cron Daemon
After=network.target

[Service]
Type=simple
ExecStart=/home/admin/openclaw/workspace/stock-assistant/inbox-cron.sh
Restart=always
RestartSec=10
StandardOutput=file:/home/admin/openclaw/workspace/logs/inbox-cron.log
StandardError=file:/home/admin/openclaw/workspace/logs/inbox-cron.log
Environment=HOME=/home/admin

[Install]
WantedBy=default.target
```

```bash
# 2. systemd user 服务：task-executor.service
[Unit]
Description=OpenClaw Task Executor
After=network.target openclaw-gateway.service

[Service]
Type=simple
ExecStart=/usr/bin/python3 /home/admin/openclaw/workspace/scripts/task_executor_daemon.py
Restart=always
RestartSec=15
StandardOutput=file:/home/admin/openclaw/workspace/logs/task-executor.log
StandardError=file:/home/admin/openclaw/workspace/logs/task-executor.log
Environment=HOME=/home/admin

[Install]
WantedBy=default.target
```

---

## 三、需要迁移的文件和目录

### 必须迁移（代码和配置）

```
/home/admin/openclaw/workspace/
├── scripts/
│   ├── inbox-disp.js          # 补货 + dispatch
│   └── task_executor.py        # 任务执行器（需改造为 daemon 版）
├── stock-assistant/
│   ├── inbox-cron.sh           # 改为 systemd 服务而非 cron 驱动
│   └── scripts/
│       ├── process_inbox.py    # inbox 处理器
│       └── dispatcher.py        # 派发器
├── HEARTBEAT.md                # heartbeat 入口定义
├── MEMORY.md                   # 长期记忆
├── USER.md                     # 用户配置
└── docs/
    └── MIGRATION-PLAN.md        # 本文档
```

### 必须迁移（数据目录）

```
/home/admin/openclaw/workspace/stock-assistant/tasks/
├── todo/      # 待办任务（持续积累）
├── doing/     # 进行中任务（每次 heartbeat 处理）
├── done/      # 已完成任务（日志）
├── inbox/     # 外部触发入口
└── blocked/   # 阻塞任务
```

### 可选迁移（已验证可重建）

```
/home/admin/openclaw/workspace/stock-assistant/tasks/failed/
/home/admin/openclaw/workspace/stock-assistant/tasks/failed/duplicates/
/home/admin/openclaw/workspace/portal/   # 展示层，可以在新环境重建
```

---

## 四、需要托管的服务

### 必须托管（3个 systemd 服务）

| 服务名 | 类型 | 作用 | 重启策略 |
|--------|------|------|----------|
| `openclaw-gateway.service` | systemd user | OpenClaw 核心运行框架 | Restart=always |
| `inbox-cron.service` | systemd user | 替代 cron 的定时触发（间隔30秒检查） | Restart=always |
| `task-executor.service` | systemd user | 从 doing 执行真实任务 | Restart=always |

### 关键设计变更

**原方案**：`inbox-cron.sh` 由 crontab `*/5 * * * *` 触发，每次启动执行一轮退出
**新方案**：`inbox-cron.service` 启动后持续运行，内部用 `sleep 30` 循环，不退出

### 不再依赖

- 系统 cron daemon（crond）
- crontab 定时器
- `process_inbox.py` 的 inbox server 机制

---

## 五、迁移步骤

### Phase 1：改造 inbox-cron.sh 为真正常驻（当前环境可做）

```bash
# 1. 重写 inbox-cron.sh 为 daemon 模式
# 不再依赖 cron 触发，改为内部 sleep 循环
```

```bash
#!/usr/bin/env bash
# inbox-cron.sh - v2.0 真正常驻 daemon
# 不再使用 trap EXIT，不再依赖 cron
# 用 systemd 管理生命周期

LOGFILE="/home/admin/openclaw/workspace/logs/inbox-cron.log"
INBOX_DISP="/home/admin/openclaw/workspace/scripts/inbox-disp.js"
TASK_EXEC="/home/admin/openclaw/workspace/scripts/task_executor.py"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') [$$] $*" >> "$LOGFILE"; }

mkdir -p "$(dirname "$LOGFILE")"

log "inbox-cron daemon v2.0 启动"

while true; do
    # 执行补货 + dispatch
    result=$(node "$INBOX_DISP" 2>/dev/null)
    if [ -n "$result" ]; then
        log "inbox-disp: $result"
    fi

    # 执行进行中的任务（最多3轮）
    for i in 1 2 3; do
        python3 "$TASK_EXEC" 2>&1 | while read line; do log "exec: $line"; done
    done

    # 休眠30秒后继续
    sleep 30
done
```

### Phase 2：创建 systemd 服务文件（当前环境可做）

```bash
mkdir -p ~/.config/systemd/user/
# 写入 inbox-cron.service
# 写入 task-executor.service（如果 task_executor.py 改为 daemon 模式）
systemctl --user daemon-reload
```

### Phase 3：目标环境部署（在新服务器执行）

```bash
# 1. 复制所有文件
rsync -avP /home/admin/openclaw/workspace/ newserver:/home/admin/openclaw/workspace/

# 2. 安装依赖
pip3 install akshare
npm install -g openclaw

# 3. 启用服务
systemctl --user enable openclaw-gateway
systemctl --user enable inbox-cron
systemctl --user enable task-executor
systemctl --user start inbox-cron

# 4. 验证
systemctl --user status inbox-cron
journalctl --user -u inbox-cron -f
```

---

## 六、验收方法

### 验证"token 未耗尽前持续工作"真正成立

**方法**：在目标环境执行以下测试

```bash
# 1. 检查服务是否真的在跑
systemctl --user status inbox-cron
# 期望：Active: active (running)

# 2. 检查进程是否真实常驻（不是 cron 触发的短暂进程）
ps aux | grep inbox-cron
# 期望：看到持续运行超过 5 分钟的进程

# 3. 检查日志是否有持续写入
tail -f ~/logs/inbox-cron.log
# 期望：每 30 秒有新行输出

# 4. 检查 done/ 任务文件是否持续增长
watch -n 10 'ls ~/workspace/stock-assistant/tasks/done/ | wc -l'
# 期望：每分钟增加

# 5. Token 消耗验证
# 24 小时后：Token 从 4500 降到 ~3500（减少约 1000）
# 证明系统在持续工作而非停摆
```

### 最低验收标准

- [ ] `systemctl --user status inbox-cron` 显示 `active (running)`
- [ ] `ps aux` 显示 inbox-cron 进程运行时间 > 10 分钟
- [ ] `done/` 目录每小时至少增加 1 个任务文件
- [ ] Token 剩余量每小时持续减少（不是停顿）

---

## 七、回滚方法

### 立即回滚（5分钟内）

```bash
# 停止新服务
systemctl --user stop inbox-cron
systemctl --user stop task-executor

# 恢复 crontab（如果有备份）
crontab -l > /tmp/crontab.backup 2>/dev/null
# 恢复 crontab 内容

# 重启旧机制
cron  # 如果可用
```

### 文件级回滚

```bash
# 用 git 回滚关键文件
cd /home/admin/openclaw/workspace
git log --oneline -5
git reset --hard <commit-hash>

# 关键回滚点
# aa1f9a0 - inbox-cron.sh 修复（最后有效版本）
# 67a1260 - 自驱补货链重构（可能引入问题）
```

### 数据回滚

- `tasks/todo/` - 任务文件，不影响系统
- `tasks/done/` - 已完成日志，不影响系统
- `tasks/inbox/` - 原始消息，可以重新入队

---

## 八、迁移前后风险点

### 迁移前风险

| 风险 | 影响 | 缓解 |
|------|------|------|
| 当前环境 cron 不可用 | inbox-cron 无法自动触发 | 依赖 heartbeat 临时维持 |
| MCP 服务器持续离线 | 持仓数据无法获取 | 已添加腾讯财经备用 |
| gateway 进程死亡 | 整体系统瘫痪 | systemd Restart=always 自动拉起 |

### 迁移中风险

| 风险 | 影响 | 缓解 |
|------|------|------|
| 服务启动失败 | 短时空窗期 | heartbeat 链路仍独立运行 |
| 文件同步中断 | 任务状态丢失 | 先同步再切换 |
| 权限问题 | 服务无法写入日志 | 提前创建目录和权限 |

### 迁移后风险

| 风险 | 影响 | 缓解 |
|------|------|------|
| systemd user session 未建立 | 服务无法启动 | 用 `loginctl enable-linger` 解决 |
| 进程数超限 | systemd 杀进程 | 配置文件设置 `TasksMax=` |
| 磁盘空间满 | 日志无法写入 | 配置 logrotate |

---

## 九、快速启动脚本（在目标环境一键运行）

```bash
#!/bin/bash
# migrate.sh - 在目标环境一键部署

WORKSPACE="$HOME/openclaw-workspace"
mkdir -p "$WORKSPACE"

# 1. 同步文件（从当前环境 scp 或 rsync）
echo "请在当前环境执行："
echo "rsync -avP /home/admin/openclaw/workspace/ targethost:$WORKSPACE/"
echo "然后继续"

# 2. 安装 Python 依赖
pip3 install akshare

# 3. 加载 systemd 服务
cp inbox-cron.service ~/.config/systemd/user/
cp task-executor.service ~/.config/systemd/user/  # 如果创建了的话
systemctl --user daemon-reload

# 4. 启用并启动
systemctl --user enable inbox-cron
systemctl --user start inbox-cron

# 5. 验证
sleep 5
systemctl --user status inbox-cron
tail "$WORKSPACE/logs/inbox-cron.log"
```
