#!/usr/bin/env node
const FS = require("fs");
const TASKS = "/home/admin/openclaw/workspace/stock-assistant/tasks";
const TODO_DIR = TASKS + "/todo";
const DOING_DIR = TASKS + "/doing";
const DONE_DIR = TASKS + "/done";

const ROUTING_TABLE = {
    "market-open-scan":  "stock-research",
    "market-close-scan": "stock-exec",
    "morning-briefing":  "stock-research",
    "stop-loss":         "stock-exec",
    "review":            "stock-review",
    "learn":             "stock-learn",
    "complex":           "stock-exec",
    "simple":            "main",
    "diagnostic":        "system",
    "cleanup":           "system",
    "repo_health":      "system",
    "idle_growth":       "system",
};

function makeResult(action, extra) {
    extra = extra || {};
    return Object.assign({ action: action, timestamp: new Date().toISOString() }, extra);
}

function getTaskType(content) {
    const m = content.match(/^type:\s*(.+)$/m);
    return m ? m[1].trim() : "unknown";
}

function claim(taskId) {
    const tp = TODO_DIR + "/" + taskId + ".md";
    const dp = DOING_DIR + "/" + taskId + ".running";
    if (!FS.existsSync(tp)) return { ok: false, reason: "todo不存在" };
    if (FS.existsSync(dp)) return { ok: false, reason: "doing已存在" };
    try { FS.renameSync(tp, dp); } catch(e) { return { ok: false, reason: "rename失败" }; }
    return { ok: true };
}

function dispatch(taskId) {
    const dp = DOING_DIR + "/" + taskId + ".running";
    if (!FS.existsSync(dp)) return { ok: false, reason: "doing文件不存在" };
    const content = FS.readFileSync(dp, "utf8");
    const taskType = getTaskType(content);
    const agent = ROUTING_TABLE[taskType] || "stock-exec";
    const msg = "任务：" + taskId + "\n类型：" + taskType + "\n执行者：" + agent + "\n时间：" + new Date().toISOString();
    return { ok: true, agent: agent, taskType: taskType, taskId: taskId, message: msg };
}

function inlineExecute(taskId) {
    const rf = DOING_DIR + "/" + taskId + ".running";
    const df = DONE_DIR + "/" + taskId + ".md";
    try {
        if (FS.existsSync(rf)) {
            const content = FS.readFileSync(rf, "utf8");
            const updated = content.replace("status: pending", "status: done");
            FS.writeFileSync(df, updated);
            FS.unlinkSync(rf);
        }
    } catch (e) { console.error("inline error: " + e.message); }
}

function handleHeartbeat() {
    const tasks = FS.readdirSync(TODO_DIR).filter(function(f){ return f.endsWith(".md"); });

    // IDLE: 生成成长任务
    if (tasks.length === 0) {
        const ts = Date.now();
        var GROWTH = [
            { id: "growth-diag-" + ts, type: "diagnostic", agent: "system" },
            { id: "growth-cleanup-" + ts, type: "cleanup", agent: "system" },
            { id: "growth-repo-" + ts, type: "repo_health", agent: "system" },
        ];
        GROWTH.forEach(function(t) {
            var lines = [
                "---",
                "type: " + t.type,
                "agent: " + t.agent,
                "status: pending",
                "priority: low",
                "id: " + t.id,
                "created: " + new Date().toISOString(),
                "来源: idle_growth",
                "---",
                "",
                "## 任务描述",
                "系统空闲时自动生成的成长任务。"
            ];
            FS.writeFileSync(TODO_DIR + "/" + t.id + ".md", lines.join("\n"));
        });
        return makeResult("idle");
    }

    // HAS TASK: claim -> dispatch
    const taskFile = tasks[0];
    const taskId = taskFile.replace(".md", "");
    const cr = claim(taskId);
    if (!cr.ok) return makeResult("claim_failed", { taskId: taskId, reason: cr.reason });

    const dr = dispatch(taskId);
    if (!dr.ok) {
        try { FS.renameSync(DOING_DIR + "/" + taskId + ".running", TODO_DIR + "/" + taskId + ".md"); } catch(e) {}
        return makeResult("dispatch_failed", { taskId: taskId, reason: dr.reason });
    }

    // growth 类型 inline 完成
    if (dr.taskType === "diagnostic" || dr.taskType === "cleanup" || dr.taskType === "repo_health") {
        inlineExecute(dr.taskId);
    }

    return makeResult("dispatched", { taskId: dr.taskId, agent: dr.agent, taskType: dr.taskType, message: dr.message });
}

const eventType = process.argv[2] || "heartbeat";
let result;
if (eventType === "heartbeat") {
    result = handleHeartbeat();
} else if (eventType === "systemEvent") {
    const event = JSON.parse(process.argv[3] || "{}");
    const taskId = "sys-" + event.type + "-" + Date.now();
    FS.writeFileSync(TODO_DIR + "/" + taskId + ".md", "type: " + event.type + "\n来源: systemEvent\n时间: " + new Date().toISOString() + "\n");
    result = handleHeartbeat();
} else {
    result = makeResult("error", { message: "未知: " + eventType });
}
console.log(JSON.stringify(result));
