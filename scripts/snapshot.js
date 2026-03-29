#!/usr/bin/env node
// scripts/snapshot.js - v1.2.5 灰度实施版
// 角色：只读展示快照生成器
// 触发方式：Gateway cron isolated session → agent exec tool → node snapshot.js
// 执行链路：Gateway cron → isolated agent turn → exec tool → node snapshot.js
// 职责：读 tasks/ 目录树 → 写 portal/status/tasks.json（只读，无其他副作用）

const FS = require("fs");
const TASKS = "/home/admin/openclaw/workspace/stock-assistant/tasks";
const PORTAL_TASKS = "/home/admin/openclaw/workspace/portal/status/tasks.json";

function scanDir(dir) {
    if (!FS.existsSync(dir)) return [];
    return FS.readdirSync(dir)
        .filter(f => f.endsWith(".md") || f.endsWith(".running"))
        .map(f => {
            const content = FS.existsSync(`${dir}/${f}`)
                ? FS.readFileSync(`${dir}/${f}`, "utf8").slice(0, 300)
                : "";
            return {
                id: f.replace(/\.(md|running)$/, ""),
                content
            };
        });
}

function generate() {
    const snap = {
        todo: scanDir(`${TASKS}/todo`),
        doing: scanDir(`${TASKS}/doing`),
        done: scanDir(`${TASKS}/done`),
        blocked: scanDir(`${TASKS}/blocked`),
        approval: scanDir(`${TASKS}/approval`),
        lastUpdated: new Date().toISOString()
    };
    FS.writeFileSync(PORTAL_TASKS, JSON.stringify(snap, null, 2));
    console.error(`[snapshot] generated: todo=${snap.todo.length} doing=${snap.doing.length} done=${snap.done.length}`);
    return snap;
}

generate();
