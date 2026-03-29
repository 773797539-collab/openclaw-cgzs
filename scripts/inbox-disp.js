#!/usr/bin/env node
// scripts/inbox-disp.js - v1.2.5 灰度实施版
// 角色：唯一执行规则源（路由逻辑）
// 执行方式：main session exec 调用，stdout 输出 JSON
// sessions_send 由 main session 自己执行（不在本文件中调用）
// stdout JSON 契约（v1.2.5）：
//   action: idle | claim_failed | dispatch_failed | dispatched
//   dispatched 时：taskId + agent + taskType + message（非空）

const FS = require("fs");

const TASKS = "/home/admin/openclaw/workspace/stock-assistant/tasks";
const TODO_DIR = `${TASKS}/todo`;
const DOING_DIR = `${TASKS}/doing`;

const ROUTING_TABLE = {
    "market-open-scan":  "stock-research",
    "market-close-scan": "stock-exec",
    "morning-briefing":  "stock-research",
    "stop-loss":         "stock-exec",
    "review":            "stock-review",
    "learn":             "stock-learn",
    "complex":           "stock-exec",
    "simple":            "main",
};

function makeResult(action, extra = {}) {
    return JSON.stringify({
        action,
        timestamp: new Date().toISOString(),
        ...extra
    });
}

function getTaskType(content) {
    const m = content.match(/type:\s*(\S+)/);
    return m ? m[1] : "simple";
}

function claim(taskId) {
    const todoPath = `${TODO_DIR}/${taskId}.md`;
    const doingPath = `${DOING_DIR}/${taskId}.running`;

    if (!FS.existsSync(todoPath)) {
        return { ok: false, reason: "todo不存在" };
    }
    if (FS.existsSync(doingPath)) {
        return { ok: false, reason: "doing已存在，拒绝重复claim" };
    }
    try {
        FS.renameSync(todoPath, doingPath);
        return { ok: true };
    } catch(e) {
        return { ok: false, reason: `文件系统错误: ${e.message}` };
    }
}

function dispatch(taskId) {
    const doingPath = `${DOING_DIR}/${taskId}.running`;
    if (!FS.existsSync(doingPath)) {
        return { ok: false, reason: "doing文件不存在" };
    }
    const content = FS.readFileSync(doingPath, "utf8");
    const taskType = getTaskType(content);
    const agent = ROUTING_TABLE[taskType] || "stock-exec";

    return {
        ok: true,
        agent,
        taskType,
        taskId,
        message: `任务：${taskId}\n类型：${taskType}\n执行者：${agent}\n时间：${new Date().toISOString()}`
    };
}

function handleHeartbeat() {
    const tasks = FS.readdirSync(TODO_DIR).filter(f => f.endsWith(".md"));
    if (tasks.length === 0) {
        return makeResult("idle");
    }

    const taskFile = tasks[0];
    const taskId = taskFile.replace(".md", "");
    const cr = claim(taskId);
    if (!cr.ok) {
        return makeResult("claim_failed", { taskId, reason: cr.reason });
    }

    const dr = dispatch(taskId);
    if (!dr.ok) {
        // 派发失败：回退到 todo/
        try {
            FS.renameSync(`${DOING_DIR}/${taskId}.running`, `${TODO_DIR}/${taskId}.md`);
        } catch(e) {}
        return makeResult("dispatch_failed", { taskId, reason: dr.reason });
    }

    // dispatched 时：taskId + agent + taskType + message（非空）
    return makeResult("dispatched", {
        taskId: dr.taskId,
        agent: dr.agent,
        taskType: dr.taskType,
        message: dr.message
    });
}

// main session 调用入口
const eventType = process.argv[2] || "heartbeat";
let result;

if (eventType === "heartbeat") {
    result = handleHeartbeat();
} else if (eventType === "systemEvent") {
    const event = JSON.parse(process.argv[3] || "{}");
    const taskId = `sys-${event.type}-${Date.now()}`;
    FS.writeFileSync(`${TODO_DIR}/${taskId}.md`, `type: ${event.type}\n来源: systemEvent\n时间: ${new Date().toISOString()}\n`);
    result = handleHeartbeat();
} else {
    result = makeResult("error", { message: `未知: ${eventType}` });
}

// stdout 输出 JSON（main session 读取此 stdout，不写文件）
console.log(result);
