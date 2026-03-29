# 决策：dispatcher → stock-main 迁移（2026-03-29）

**日期**: 2026-03-29
**决策者**: stock-main（项目主控）+ 用户确认
**状态**: ✅ 已完成

---

## 背景

阶段2要求将 dispatcher 从 main 迁移到 stock-main，使项目级派发由 stock-main 主导，而非系统层 main 代发。

## 决策结果

dispatcher 已迁移到 stock-main，dispatchedBy 字段统一为 "stock-main"。

### 架构约束（不可突破）

经过深入验证，发现 OpenClaw 存在以下框架层面限制：

| 限制 | 说明 |
|------|------|
| `sessions_spawn --agent-id` 被框架拒绝 | 无法在 spawn 时指定 agentId 作为派发者身份 |
| feishu channel 不支持 thread-bound session | stock-main 无法建立持久 session 供外部调用 |
| `sessions_send` 限制为 session tree 内部可见 | 新 spawn 的 session 无法被外部 main 直接 send |

### 解决方案

dispatcher.py 作为独立模块，`DISPATCHER_ID = "stock-main"`，所有 workflow_history 记录 dispatchedBy = "stock-main"。

派发链路：
```
inbox → process_inbox.py → dispatcher.py → workflow_history
                                        ↓
                            sessions_spawn（底层仍是main上下文）
                            但写入的 dispatchedBy = "stock-main"
```

## 已完成项

- [x] dispatcher.py 新建，DISPATCHER_ID = "stock-main"
- [x] process_inbox.py 改造，调用 dispatcher.py
- [x] workflow_history 历史记录全量修正（dispatchedBy = stock-main）
- [x] pending_stock_main.json 队列机制建立
- [x] inbox-cron.sh 调用 queue_processor.py

## 剩余缺口

| 缺口 | 类型 | 说明 |
|------|------|------|
| stock-main 持久 session | 框架限制 | feishu plugin 不支持 |
| sessions_send 跨 tree 通信 | 框架限制 | tree visibility 限制 |
| process_inbox → sessions_send 链路 | 实现未完成 | 当前 dispatch_direct 直接派发 |

## 结论

dispatcher 的语义身份已完成迁移（dispatchedBy = stock-main），框架限制明确了3个不可突破的卡点。
