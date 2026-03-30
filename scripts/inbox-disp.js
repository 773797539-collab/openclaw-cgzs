#!/usr/bin/env node
/**
 * inbox-disp.js - v1.3.0 真实任务补货版
 *
 * 核心职责：
 * 1. inbox 有文件 → 移动到 todo/
 * 2. inbox 空 + todo < 3 → 从真实任务模板补货到 todo >= 3
 * 3. todo > 0 → dispatch 最老任务（inline 完成 growth 类型）
 *
 * 不再生成无意义的 growth-* 任务占位。
 */
const FS = require("fs");
const PATH = require("path");

const TASKS = "/home/admin/openclaw/workspace/stock-assistant/tasks";
const INBOX_DIR  = TASKS + "/inbox";
const TODO_DIR   = TASKS + "/todo";
const DOING_DIR  = TASKS + "/doing";
const DONE_DIR   = TASKS + "/done";
const FAILED_DIR = TASKS + "/failed";
const BLOCKED_DIR = TASKS + "/blocked";

const LOW_WATER = 3; // 待办最低水位

// ============================================================
// 任务模板库（8类保底任务）
// ============================================================
const TASK_TEMPLATES = [
    {
        id_prefix: "sys-diag",
        type: "diagnostic",
        agent: "system",
        priority: "low",
        title: "系统诊断",
        description: "执行诊断检查：\n1. 检查 MCP 服务器连通性（82.156.17.205:8000）\n2. 检查 inbox-cron daemon 进程状态\n3. 检查 cron daemon 是否存活\n4. 检查 portal 展示状态与真实状态一致性\n5. 输出诊断结果到 logs/diagnostic-YYYYMMDD.log"
    },
    {
        id_prefix: "sys-cleanup",
        type: "cleanup",
        agent: "system",
        priority: "low",
        title: "清理任务",
        description: "执行清理：\n1. 统计 tasks/done/ 文件数量\n2. 清理 tasks/done/ 下超过7天的 .md 文件\n3. 清理 tasks/failed/ 下的孤立的 .failed 文件\n4. 检查并清理 tasks/doing/ 下超过2小时的 .running 文件\n5. 记录清理结果"
    },
    {
        id_prefix: "sys-consistency",
        type: "consistency_check",
        agent: "system",
        priority: "low",
        title: "真值层一致性检查",
        description: "执行真值层一致性检查：\n1. 对比 tasks/todo/ 文件数与 tasks.json 的 todo 计数\n2. 对比 tasks/doing/ 文件数与 tasks.json 的 doing 计数\n3. 对比 tasks/done/ 文件数与 tasks.json 的 done 计数\n4. 检查 .running 文件是否与 doing 文件一一对应\n5. 检查 snapshot 文件是否与 tasks 目录同步\n6. 输出差异报告"
    },
    {
        id_prefix: "sys-blocked",
        type: "blocked_review",
        agent: "system",
        priority: "medium",
        title: "blocked 任务复查",
        description: "复查 blocked 目录：\n1. 列出 tasks/blocked/ 所有任务\n2. 检查每个 blocked 任务是否仍处于 blocked 状态\n3. 尝试重新激活可以恢复的任务到 todo/\n4. 更新 blocked 记录，标注原因和时间\n5. 输出复查结果"
    },
    {
        id_prefix: "sys-docs",
        type: "docs_review",
        agent: "system",
        priority: "low",
        title: "docs 现状差异扫描",
        description: "扫描 docs 目录与实际实现差异：\n1. 对比 docs/ 下的架构文档与实际目录结构\n2. 检查 scripts/ 下的脚本是否有对应的说明文档\n3. 检查 changelog 是否与最近 git log 一致\n4. 列出需要更新的文档清单\n5. 更新 docs/changelog/project-change-log.md（如有必要）"
    },
    {
        id_prefix: "sys-heartbeat",
        type: "heartbeat_review",
        agent: "system",
        priority: "medium",
        title: "heartbeat / cron 健康复查",
        description: "heartbeat 和 cron 健康检查：\n1. 检查 /tmp/inbox-cron.log 最近5行是否有错误\n2. 检查 cron daemon 进程是否存在\n3. 检查 openclaw-gateway 进程是否存活\n4. 检查 HEARTBEAT.md 约定的各项检查是否正常\n5. 检查 snapshot-refresh cron job 是否正常触发\n6. 输出健康报告"
    },
    {
        id_prefix: "sys-portal",
        type: "portal_review",
        agent: "system",
        priority: "low",
        title: "门户展示一致性复查",
        description: "portal 展示与真实状态一致性检查：\n1. 读取 tasks.json 的 todo/doing/done 计数\n2. 统计 tasks/todo/、tasks/doing/、tasks/done/ 实际文件数\n3. 对比差异，如有差异则更新 tasks.json\n4. 检查 portal/status/system.json 是否存在且有效\n5. 检查 portal 页面是否可访问（curl localhost:8081）"
    },
    {
        id_prefix: "sys-failed",
        type: "failed_review",
        agent: "system",
        priority: "medium",
        title: "失败样本整理",
        description: "整理失败任务样本：\n1. 列出 tasks/failed/ 下所有失败任务\n2. 统计失败类型分布（网络/权限/语法/超时）\n3. 分析每个失败原因\n4. 对于可重试的任务，尝试重新派发\n5. 对于重复失败的任务，移动到 archive/\n6. 输出失败分析报告"
    }
];

/**
 * 从模板生成真实任务文件，写入 todo/
 */
function generateFromTemplate(template) {
    const ts = Date.now();
    const id = template.id_prefix + "-" + ts;
    const lines = [
        "---",
        "type: " + template.type,
        "agent: " + template.agent,
        "status: pending",
        "priority: " + template.priority,
        "id: " + id,
        "created: " + new Date().toISOString(),
        "来源: idle_replenish",
        "title: " + template.title,
        "---",
        "",
        "## 任务描述",
        template.description
    ];
    const filePath = TODO_DIR + "/" + id + ".md";
    FS.writeFileSync(filePath, lines.join("\n"));
    return id;
}

/**
 * 补充任务到最低水位
 */
function replenishToWaterLevel() {
    const existing = FS.readdirSync(TODO_DIR).filter(f => f.endsWith(".md"));
    const count = existing.length;
    if (count >= LOW_WATER) {
        return 0; // 水位已满足
    }

    // 每次轮换选一个不同的模板（按模板索引轮询）
    replenishToWaterLevel._counter = replenishToWaterLevel._counter || 0;
    const need = LOW_WATER - count;
    const added = [];

    for (let i = 0; i < need; i++) {
        const idx = (replenishToWaterLevel._counter + i) % TASK_TEMPLATES.length;
        const tid = generateFromTemplate(TASK_TEMPLATES[idx]);
        added.push(tid);
    }
    replenishToWaterLevel._counter = (replenishToWaterLevel._counter + need) % TASK_TEMPLATES.length;
    return added.length;
}

// ============================================================
// 核心逻辑
// ============================================================
function makeResult(action, extra) {
    return JSON.stringify(Object.assign({action, timestamp: new Date().toISOString()}, extra || {}));
}

function claimTask(taskId) {
    // 移动 .md 文件到 doing/
    const src = TODO_DIR + "/" + taskId + ".md";
    const dst = DOING_DIR + "/" + taskId + ".md";
    if (FS.existsSync(src)) {
        FS.renameSync(src, dst);
    }
    // 创建 .running 标记
    FS.writeFileSync(DOING_DIR + "/" + taskId + ".running", String(Date.now()));
}

function completeTask(taskId, taskType) {
    const src = DOING_DIR + "/" + taskId + ".md";
    const dst = DONE_DIR + "/" + taskId + ".md";
    if (FS.existsSync(src)) {
        FS.renameSync(src, dst);
    } else {
        // inline complete（没文件也要写入 done）
        const lines = [
            "---",
            "type: " + taskType,
            "agent: system",
            "status: done",
            "id: " + taskId,
            "completed: " + new Date().toISOString(),
            "---"
        ];
        FS.writeFileSync(dst, lines.join("\n"));
    }
    // 删除 .running
    try { FS.unlinkSync(DOING_DIR + "/" + taskId + ".running"); } catch(e) {}
}

function processInbox() {
    if (!FS.existsSync(INBOX_DIR)) FS.mkdirSync(INBOX_DIR, {recursive: true});
    if (!FS.existsSync(TODO_DIR))  FS.mkdirSync(TODO_DIR,  {recursive: true});
    if (!FS.existsSync(DOING_DIR)) FS.mkdirSync(DOING_DIR, {recursive: true});
    if (!FS.existsSync(DONE_DIR))  FS.mkdirSync(DONE_DIR,  {recursive: true});

    const files = FS.readdirSync(INBOX_DIR).filter(f => f.endsWith(".md"));
    let processed = 0;
    for (const file of files) {
        const src = INBOX_DIR + "/" + file;
        const id = file.replace(".md", "");
        const dst = TODO_DIR + "/" + file;
        if (!FS.existsSync(dst)) {
            FS.renameSync(src, dst);
            processed++;
        }
    }
    return processed;
}

function main() {
    processInbox(); // 处理 inbox 文件

    const tasks = FS.readdirSync(TODO_DIR).filter(f => f.endsWith(".md"));

    // 主循环：补满水位，然后 dispatch 直到水位达标
    // 每次调用尽量让 todo 达到 LOW_WATER
    let added = 0;
    while (true) {
        const current = FS.readdirSync(TODO_DIR).filter(f => f.endsWith(".md")).length;
        if (current < LOW_WATER) {
            const newCount = replenishToWaterLevel();
            if (newCount === 0) break; // 没有更多模板
            added += newCount;
        } else {
            break;
        }
    }

    // 现在 todo >= LOW_WATER，dispatch 直到低于水位
    const dispatchees = [];
    while (true) {
        const remaining = FS.readdirSync(TODO_DIR).filter(f => f.endsWith(".md"));
        if (remaining.length <= LOW_WATER - 1) break; // 保持 todo >= LOW_WATER

        remaining.sort();
        const taskFile = remaining[0];
        const taskId = taskFile.replace(".md", "");
        claimTask(taskId);

        const content = FS.readFileSync(DOING_DIR + "/" + taskId + ".md", "utf8");
        const typeMatch = content.match(/^type:\s*(.+)$/m);
        const taskType = typeMatch ? typeMatch[1].trim() : "unknown";

        // growth/diagnostic/cleanup inline 完成，其他类型保留 doing
        // 所有任务都只 dispatch 到 doing，不做 inline complete
        // 真实执行由 task_executor.py 处理
        dispatchees.push({taskId, taskType});
    }

    if (dispatchees.length > 0) {
        const last = dispatchees[dispatchees.length - 1];
        return makeResult("dispatched", {
            taskId: last.taskId,
            agent: "system",
            taskType: last.taskType,
            dispatchedCount: dispatchees.length,
            message: `批量派发${dispatchees.length}个任务，最后执行: ${last.taskId} (${last.taskType})`
        });
    }
    return makeResult("idle");
}

process.stdout.write(main());
