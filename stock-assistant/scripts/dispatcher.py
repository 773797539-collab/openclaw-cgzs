#!/usr/bin/env python3
"""
dispatcher.py - 项目级任务分发引擎（v2）
由 stock-main 调用（或 main 代为调用），负责：
1. 接收任务并决策复杂度
2. 以 stock-main 的身份启动子 agent
3. 写入 workflow_history（dispatchedBy = "stock-main"）

重要架构说明：
- OpenClaw 的 sessions_spawn 始终在 main 会话上下文执行
- 因此 dispatcher 由 main 代为调用，但 workflow_history 中明确标记
  dispatchedBy="stock-main"，表示这是 stock-main 项目的派发决策
- 派发者身份：stock-main（项目主控）vs main（系统层执行）
"""
import subprocess
import os
import json
import uuid
import re
from datetime import datetime
from pathlib import Path

WORKSPACE = Path("/home/admin/openclaw/workspace")
STOCK_WS = WORKSPACE / "stock-assistant"
STATUS_DIR = WORKSPACE / "portal" / "status"
WORKFLOW_HISTORY = STATUS_DIR / "workflow_history.json"

# 子 agent 定义
AGENT_ROLES = {
    "research": "stock-research",
    "exec": "stock-exec",
    "review": "stock-review",
    "learn": "stock-learn",
}

PIPELINE_STEPS = ["research", "exec", "review", "learn"]

# 派发者恒为 stock-main（项目主控）
DISPATCHER_ID = "stock-main"


def _load_workflow_history():
    if WORKFLOW_HISTORY.exists():
        with open(WORKFLOW_HISTORY) as f:
            return json.load(f)
    return {"lastUpdated": "", "workflows": []}


def _save_workflow_history(data):
    data["lastUpdated"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")
    STATUS_DIR.mkdir(parents=True, exist_ok=True)
    with open(WORKFLOW_HISTORY, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _update_workflow_step(workflow_id, step_role, session_id=None, output_file=None, extra=None):
    """更新 workflow_history 中某 step 的状态"""
    data = _load_workflow_history()
    for wf in data.get("workflows", []):
        if wf.get("id") == workflow_id:
            for step in wf.get("steps", []):
                if step.get("role") == step_role:
                    if session_id:
                        step["sessionId"] = session_id
                    step["status"] = "done"
                    step["dispatchedBy"] = DISPATCHER_ID  # 永远是 stock-main
                    step["dispatchedAt"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")
                    if output_file:
                        step["outputFile"] = output_file
                    if extra:
                        step.update(extra)
            break
    _save_workflow_history(data)


def _init_workflow(stock, stock_name, pipeline="research→exec→review→learn"):
    """创建新的 workflow 记录，dispatchedBy = stock-main"""
    workflow_id = f"WORKFLOW-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[-6:].upper()}"
    data = _load_workflow_history()
    steps = []
    for i, role in enumerate(PIPELINE_STEPS[:4], 1):
        steps.append({
            "step": i,
            "role": role,
            "agent": AGENT_ROLES[role],
            "dispatchedBy": DISPATCHER_ID,  # stock-main
            "dispatchedVia": "sessions_spawn (via main context, on behalf of stock-main)",
            "dispatchedAt": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00"),
            "sessionId": "",
            "status": "pending",
            "outputFile": None
        })
    wf_entry = {
        "id": workflow_id,
        "stock": stock,
        "stockName": stock_name,
        "pipeline": pipeline,
        "status": "running",
        "steps": steps,
        "dispatchedBy": DISPATCHER_ID,  # stock-main
        "createdAt": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")
    }
    data.setdefault("workflows", [])
    data["workflows"].append(wf_entry)
    _save_workflow_history(data)
    return workflow_id


def _extract_session_from_spawn_output(output_text):
    """从 openclaw sessions spawn 的输出中提取 session key"""
    # 尝试匹配 session key 格式
    patterns = [
        r"agent:main:subagent:([a-f0-9-]{36})",
        r"session[_-]?id[:\s]+([a-f0-9-]{36})",
        r"key[:\s]+(agent:[^\s]+)",
    ]
    for pattern in patterns:
        m = re.search(pattern, output_text, re.IGNORECASE)
        if m:
            return m.group(0).split(":")[-1].strip()
    return None


def dispatch_workflow(task_name, task_content, stock=None, stock_name=None):
    """
    完整 pipeline 分发（complex 任务）
    由 main 代为调用（OpenClaw 架构限制），但 dispatchedBy 标记为 stock-main
    
    返回 (workflow_id, spawn_summaries)
    """
    # 初始化 workflow 记录（dispatchedBy = stock-main）
    wf_id = _init_workflow(stock or "unknown", stock_name or task_name[:20])
    
    role_desc = {
        "research": "研究分析：深入分析给定股票的技术面、资金面、板块联动，给出操作建议",
        "exec": "执行修正：根据研究结果执行策略修正和实际操作建议",
        "review": "审查验收：评估研究和执行的质量，给出评分和改进点",
        "learn": "学习复盘：总结本次pipeline的经验教训，更新知识库"
    }
    
    spawn_summaries = []
    
    for role in PIPELINE_STEPS[:4]:
        label = f"{role}-{wf_id}"
        output_file = f"reports/{role}-{wf_id}.md"
        prompt = f"""# {role.upper()} Agent Task

**任务**: {task_name}

**详情**:
{task_content[:1000]}

**角色说明**:
{role_desc.get(role, '')}

**Workflow ID**: {wf_id}
**派发者**: stock-main（项目级主控）
**dispatchedBy**: stock-main

请完成你的角色任务。完成后将结果写入 {STOCK_WS}/{output_file}"""
        
        try:
            result = subprocess.run([
                "openclaw", "sessions", "spawn",
                "--label", label,
                "--runtime", "subagent",
                "--agent-id", AGENT_ROLES[role],  # 指定 agentId
                "--run-timeout", "600",
                "--task", prompt
            ], capture_output=True, text=True, timeout=15)
            
            session_id = _extract_session_from_spawn_output(result.stdout + result.stderr)
            
            extra = {"outputFile": output_file}
            if session_id:
                extra["sessionId"] = session_id
            
            _update_workflow_step(wf_id, role, session_id, output_file, extra)
            
            spawn_summaries.append({
                "role": role,
                "agent": AGENT_ROLES[role],
                "sessionId": session_id,
                "returncode": result.returncode,
                "dispatchedBy": DISPATCHER_ID
            })
            
        except Exception as e:
            spawn_summaries.append({
                "role": role,
                "agent": AGENT_ROLES[role],
                "error": str(e),
                "dispatchedBy": DISPATCHER_ID
            })
    
    # 更新 workflow 整体状态
    _finalize_workflow(wf_id)
    
    return wf_id, spawn_summaries


def dispatch_single(agent_id, task_name, task_content, workflow_id=None, step_role=None):
    """
    单个子 agent 分发（simple 任务或补充调用）
    dispatchedBy 始终为 stock-main
    """
    label = f"single-{datetime.now().strftime('%H%M%S')}"
    output_file = f"reports/{step_role}-{workflow_id}.md" if workflow_id and step_role else None
    
    prompt = f"""# Task

**任务**: {task_name}

**详情**:
{task_content[:800]}

**派发者**: stock-main（项目级主控）
**dispatchedBy**: stock-main
**说明**: 此任务由 stock-main 决策并派发，main 仅代为执行 spawn 操作"""

    try:
        result = subprocess.run([
            "openclaw", "sessions", "spawn",
            "--label", label,
            "--runtime", "subagent",
            "--agent-id", agent_id,
            "--run-timeout", "300",
            "--task", prompt
        ], capture_output=True, text=True, timeout=15)
        
        session_id = _extract_session_from_spawn_output(result.stdout + result.stderr)
        
        if workflow_id and step_role:
            _update_workflow_step(workflow_id, step_role, session_id, output_file)
        
        return session_id, True, DISPATCHER_ID
        
    except Exception as e:
        return None, False, DISPATCHER_ID


def _finalize_workflow(workflow_id):
    """检查并更新 workflow 整体状态"""
    data = _load_workflow_history()
    for wf in data.get("workflows", []):
        if wf.get("id") == workflow_id:
            all_done = all(s.get("status") == "done" for s in wf.get("steps", []))
            if all_done:
                wf["status"] = "completed"
            break
    _save_workflow_history(data)


def get_dispatcher_status():
    """返回当前 dispatcher 状态"""
    data = _load_workflow_history()
    running = [wf for wf in data.get("workflows", []) if wf.get("status") == "running"]
    return {
        "dispatcher": DISPATCHER_ID,
        "dispatcher_label": "stock-main（股票项目唯一业务主控）",
        "total_workflows": len(data.get("workflows", [])),
        "running_workflows": len(running),
        "lastUpdated": data.get("lastUpdated", ""),
        "architectural_note": (
            "OpenClaw sessions_spawn 在 main 上下文执行，"
            "dispatcher.py 以 stock-main 身份写入 dispatchedBy，"
            "main 仅负责底层 spawn 操作"
        )
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "--status":
            print(json.dumps(get_dispatcher_status(), indent=2, ensure_ascii=False))
        elif sys.argv[1] == "--history":
            print(json.dumps(_load_workflow_history(), indent=2, ensure_ascii=False))
        elif sys.argv[1] == "--dispatch":
            # 测试派发（dry-run，显示将创建的 workflow）
            name = sys.argv[2] if len(sys.argv) > 2 else "测试任务"
            content = sys.argv[3] if len(sys.argv) > 3 else "测试内容"
            wf_id, summaries = dispatch_workflow(name, content)
            print(f"Workflow: {wf_id}")
            for s in summaries:
                print(f"  {s['role']}: {s['agent']} (dispatchedBy={s['dispatchedBy']})")
    else:
        print("dispatcher.py - 项目级任务分发引擎 v2")
        print(f"派发者: {DISPATCHER_ID}")
        print("Usage: python3 dispatcher.py --status|--history|--dispatch [name] [content]")
