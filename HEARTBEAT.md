# HEARTBEAT.md

## 入口路由规则

**入口**：`inbox/` 目录下的 .md 文件
**处理**：每次 heartbeat 执行：
1. `process_inbox.py` → 扫描 inbox，空时调用 `inbox-disp.js` 补货到 todo≥3，dispatch 到 doing
2. `task_executor.py` → 从 doing 执行真实任务，写真实结果到 done（最多3轮）
**dispatchedBy**：dispatcher.py 内部硬编码为 "stock-main"

## Pending 队列处理（每次 heartbeat 执行）

**处理流程**：
```
exec(command="cd /home/admin/openclaw/workspace/stock-assistant && python3 scripts/process_inbox.py 2>&1")
```

**cron 触发**：系统cron每5分钟唤醒 agent，确保队列不积压。

## 内部任务池处理（每次 heartbeat 执行）

**核心原则：有 Token 就干活，doing 有任务就执行，不空转**

**每次 heartbeat 执行**：
```bash
# 1. 补货 + dispatch（inbox → todo → doing）
python3 /home/admin/openclaw/workspace/stock-assistant/scripts/process_inbox.py

# 2. 执行 doing 中的真实任务（最多3轮）
for i in 1 2 3; do python3 /home/admin/openclaw/workspace/scripts/task_executor.py; done
```
- 先查 Token，Token=0 则静默停摆
- process_inbox.py：inbox 空时从 8 类保底模板补货到 todo≥3，dispatch 到 doing
- task_executor.py：从 doing 取任务执行，写真实结果到 done/

**内部任务池永远不会空**，因为：
- 初始11个任务（系统维护/诊断/清理）
- 每轮自动补充新任务（日报/git/cron等轮询任务）
- failed 的任务自动重置重试

**注意**：系统无 cron daemon，daemon 仅作备用。主力是每次 heartbeat 批量执行5个任务。

## Token 检查规则（最重要！）

**每次 heartbeat 必须先运行 token_guard**：
```python
# heartbeat 开头必须先调用
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
2. **内部任务池** - 从池中取一个 pending 任务执行（token_guard 之后立即执行）
3. **Portal 运行状态** - 每 heartbeat 检查
4. **Git 提交** - 每 heartbeat 有事实产出（有任务执行就有 commit）
5. **Memory 更新** - 每天 review

**内部任务池永不空**：
- 初始11个任务（系统维护/诊断/清理）
- 每次补充新任务
- failed 自动重置重试

## 当前状态（2026-03-29 15:52）

```
Token：4458/4500（99.1%），约4.1小时
Portal：✅ 正常（5 agents）
持仓：立达信 605365，¥18.35，浮亏-11.2%
今日：周日休市，下一工作日周一09:30
Git：9362281（96条）
工作区：干净
队列：0条待处理
taskPool：todo=0 doing=0 done=2 blocked=0
系统：健康
cron：4个（周一至五，market-open/close + morning + inbox）
最近commit：dispatcher迁移决策文档
```

## Token汇报格式
```
Token: 剩余A/B=A%, 已用(B-A)/B=B%  ✅/⚠️/❌
判断: remaining > 0 → 继续工作；remaining = 0 → 静默停摆
```

## 静默停摆规则（硬规）

**触发以下任一条件，立即停摆，不发任何消息**：
1. Token API 返回 usage_count = 0
2. Token API 返回 HTTP 错误或 JSON 解析失败
3. Token 剩余 < 20%（即 4.3% 已触发）
4. Portal API 无响应

**静默停摆 = 不回复任何 channel，不写日志，只记录 HEARTBEAT_OK**
