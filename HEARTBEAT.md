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

**cron 触发**：系统cron每5分钟唤醒 agent，确保队列不积压。

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
2. **Portal 运行状态** - 每 heartbeat 检查
3. **Git 提交** - 每 heartbeat 有事实产出
4. **Memory 更新** - 每天 review

**内部任务池**（无外部任务时）：
- 工作流优化 / 提示词改进 / 失败样本 / 验收规则 / SOP / 复盘
- docs/ 文档完善
- 代码去重和规范

## 当前状态（2026-03-29 15:22）

```
Token：4500/4500（100%），约4.6小时 ✨新周期
Portal：✅ 正常（5 agents）
持仓：立达信 605365，¥18.35，浮亏-11.2%
今日：周日休市，下一工作日周一09:30
Git：29b2db2
工作区：干净
队列：0条待处理
系统：健康
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
