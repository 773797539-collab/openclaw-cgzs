# cron → agent 集成问题分析与修复

**日期**: 2026-03-28  
**状态**: ✅ 已修复

---

## 问题描述

定时任务 cron 触发时，main agent 收到 `systemEvent` 但未执行 coord 脚本。

## 根因

1. OpenClaw cron job 配置 `systemEvent: market-open-scan` → main
2. main 的 handleMessage 未覆盖 `systemEvent` 类型
3. 导致 cron 触发但无实际业务执行

## 修复方案

### 方案：系统 crontab 直接调用 coord（绕过 main）

```bash
# 开盘扫描（周一至周五 09:00）
0 9 * * 1-5 cd /home/admin/openclaw/workspace && python3 stock-assistant/scripts/market_open_coord.py >> logs/market-open.log 2>&1

# 收盘扫描（周一至周五 16:00）
0 16 * * 1-5 cd /home/admin/openclaw/workspace && python3 stock-assistant/scripts/market_close_coord.py >> logs/market-close.log 2>&1
```

### coord 脚本职责

market_open_coord.py：
- 检查是否交易日
- 确保 crontab 注册
- 调用 market_open_scan.py

market_close_coord.py：
- 检查是否交易日
- 确保 crontab 注册
- 调用 market_close_scan.py

### 为什么不用 OpenClaw cron exec 模式

OpenClaw cron 支持 `exec` 模式直接运行命令，但：
1. 需改所有 cron job 的 `sessionTarget: null`
2. 改动面大，风险高
3. 系统 crontab 更简单直接

---

## 验证

```bash
# 检查 crontab
crontab -l | grep coord

# 测试（非交易时段应跳过）
python3 stock-assistant/scripts/market_open_coord.py
python3 stock-assistant/scripts/market_close_coord.py
```
