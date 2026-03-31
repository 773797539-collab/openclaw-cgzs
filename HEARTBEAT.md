# HEARTBEAT.md

## 入口路由规则

**入口**：`inbox/` 目录下的 .md 文件
**处理**：每次 heartbeat 执行 `task_executor.py` 批循环（最多10个任务，完成→立即接下一个）

## 内部任务池处理

**核心原则：有 Token 就干活，完成→立即接下一个，不等定时器**

**每次 heartbeat 执行**：
```bash
python3 /home/admin/openclaw/workspace/scripts/task_executor.py
```
- 先查 Token，Token=0 则静默停摆
- task_executor 内部自动：完成→检查todo水位→补货→派发→接下一个（0秒间隔）
- MAX_BATCH=10，BATCH_SLEEP=0
- 停止条件：Token≤20%、无可执行任务、所有优先级任务因minInterval不可执行

**inbox-disp.js 补货逻辑（task_executor 内部调用）**：
- 严格 P0→P1→P2→P3 优先级
- P0 永远维持≥2个，P0<2时忽略minInterval强制补
- P1+P2合计最多占todo的1/3
- P3只在P0/P1/P2都没有时出现

**23个P0模板**：持仓扫描、观察池扫描、异动监控、盘前任务（市场环境/热点板块/持仓重点/今日重点3股/风险提醒/行动计划）、盘中任务（公告变化/环境切换/强时效提醒）、盘后任务（市场复盘/持仓复盘/选股复盘/错误归因/次日准备）、资产更新（holdings/watchlist/related/recent）

## Token 检查规则（最重要！）

**每次 heartbeat 必须先运行 token_guard**：
```python
import sys
sys.path.insert(0, '/home/admin/openclaw/workspace/scripts')
from heartbeat_token_guard import check_token
if not check_token():
    exit(0)  # 静默停摆，HEARTBEAT_OK也不发
```

**token_guard 内部逻辑**：
1. 调用 MiniMax API 查 Token
2. 找到 MiniMax-M* 的 usage_count（=剩余）和 total_count（=总额）
3. remaining > 0 → 打印状态，继续工作
4. remaining = 0 或 API 失败 → **静默停摆**，不发任何消息

## Portal 健康检查
```bash
curl -s http://localhost:8081/api/status/all | python3 -c "import sys,json; d=json.load(sys.stdin); g=d.get('governance',{}); p=d.get('portfolio',{}); h=p.get('holdings',[]); hv=h[0] if h else {}; print('portal_ok agent=%s val=%s' % (g.get('agent_count','?'), int(float(hv.get('price',0))*hv.get('shares',0)) if hv else 0))"
```
如果 DOWN，杀掉重启：
```bash
pkill -f "python3.*portal"; sleep 1; cd /home/admin/openclaw/workspace/portal && nohup python3 server.py > /tmp/portal.log 2>&1 &
```

## 标准检查（按优先级）

1. **Token 状态** - 先查，0则静默停摆
2. **内部任务池** - task_executor 批循环执行（不等待定时器）
3. **Portal 运行状态** - 每 heartbeat 检查
4. **Git 提交** - 每 heartbeat 有事实产出

## Token汇报格式
```
Token: 剩余A/B=A%, 已用(B-A)/B=B%  ✅/⚠️/❌
判断: remaining > 0 → 继续工作；remaining = 0 → 静默停摆
```

## 静默停摆规则（硬规）

**触发以下任一条件，立即停摆，不发任何消息**：
1. Token API 返回 usage_count = 0
2. Token API 返回 HTTP 错误或 JSON 解析失败
3. Token 剩余 < 20%
4. Portal API 无响应

**静默停摆 = 不回复任何 channel，不写日志，只记录 HEARTBEAT_OK**

## 当前状态（2026-03-31 03:17）

```
Token：3993/4500（88.7%），已用11.3%，充足 ✅
Portal：✅ 正常（5 agents），持仓市值¥1864
持仓：立达信 605365
观察池：002042 华孚时尚
done：1344个（P0模板循环，无真实业务结果时全跳过）
Git：e549978（最新commit）
系统：健康
```

## 阶段6完成标志

**已接通**：
- add-holding → inbox任务 → todo → doing → execute_portfolio_scan → 回写holdings.json → done
- add-watch → inbox任务 → todo → doing → execute_portfolio_scan → 回写watchlist.json → done
- execute_portfolio_scan 真实运行（无NameError）
- done记录有真实业务结论（持仓风险/观察池扫描）

**done口径（严格执行）**：
- execute_diagnostic → {} → 不进done
- execute_lightweight → None → 不进done
- execute_portfolio_scan → 真实结论dict → 进done
