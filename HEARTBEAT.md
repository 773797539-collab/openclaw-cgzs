# HEARTBEAT.md

## 入口路由规则

**入口**：`inbox/` 目录下的 .md 文件
**处理**：每次 heartbeat 执行 `process_inbox.py`，它扫描 inbox 并通过 `dispatcher.py` 派发任务
**dispatchedBy**：dispatcher.py 内部硬编码为 "stock-main"

## Pending 队列处理（每次 heartbeat 执行）

**处理流程**：
```
exec(command="cd /home/admin/openclaw/workspace/stock-assistant && python3 scripts/process_inbox.py 2>&1")
```

**cron 触发**：系统cron每5分钟（OpenClaw inbox cron已禁用）【已禁用】唤醒 agent，确保队列不会积压太久。



## Portal 健康检查
```bash
curl -s http://localhost:8081/api/status/all | python3 -c "import sys,json; d=json.load(sys.stdin); g=d.get('governance',{}); p=d.get('portfolio',{}); h=p.get('holdings',[]); hv=h[0] if h else {}; print('portal_ok agent=%s val=%s' % (g.get('agent_count','?'), int(float(hv.get('price',0))*hv.get('shares',0)) if hv else 0))"
```
如果 DOWN，杀掉重启：
```bash
pkill -f "python3.*portal"; sleep 1; cd /home/admin/openclaw/workspace/portal && nohup python3 server.py > /tmp/portal.log 2>&1 &
```

## 标准检查（按优先级）
1. **Portal 运行状态** - 每 heartbeat 检查
2. **Git 提交** - 每 heartbeat 有事实产出
3. **Memory 更新** - 每天 review
**内部任务池**：工作流优化 / 提示词 / 失败样本 / 验收规则 / 去重 / SOP / 复盘 / 研究

## 当前状态（2026-03-28 16:29）

```
当前周期：周期4（15:00–20:00）←刚重置
周期总额度：4500
当前剩余：约4305（95.7%）
当前已用：约195（4.3%）
Portal：✅ 5 agents，市值¥1835
持仓：立达信 605365，¥18.35（昨收），浮亏-11.2%
今日收盘：上证3902.47 ▲2.14%，创业板▲2.88%
周六休市，下一工作日：周一09:30
磁盘：32GB可用，17%使用率，健康
backups/：已清理到1个文件(301MB)，释放170MB
```

**16:22后主动工作（不等触发）**：
- evolution IDEA_LOG追加被动触发根因分析
- backups/清理3个旧备份，释放170MB
- system.json gitCommit更新（9723ab9→d72de2d）
- 15个脚本语法全部OK
- 6个cron正常（周一00:30止损监控）
- 所有data/ JSON文件正常
- strategy.json vs alert_config.json 配置不一致已澄清（不需修改）
- changelog追加下午变更记录（停摆事件+cron状态+代码修复+运维）

---

## 今日状态（2026-03-29）

**Token**: 99.7%（1.9小时剩余）✅
**Git**: master已同步（4db5626）
**系统cron**: process_inbox.py 每5分钟 ✅
**Portal**: 正常
**workflow**: 20+条完成，0条进行中

**多Agent验收（2026-03-29）**：
- stock-main主控session ✅
- dispatchedBy=stock-main ✅
- workflow样本：WORKFLOW-20260329-7B561D/✅
- 阶段2入口唯一化：系统cron(*/5 * * * *) ✅

## 入口路由（最终版）

**生产入口**：inbox/ → 系统cron → process_inbox.py → dispatcher → workflow
**dispatchedBy**: stock-main（硬编码）

## Token汇报格式
```
Token: 剩余A/B=A%, 已用(B-A)/B=B%  ✅
判断: remaining > 0 → 继续工作
```
