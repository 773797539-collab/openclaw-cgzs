#!/usr/bin/env node
// snapshot.js - 任务看板快照生成器（v2）
// 读取 tasks/{todo,doing,done,blocked,approval}/ 目录树
// 解析 YAML frontmatter，提取关键字段，写入 tasks.json
// 不再写入原始 content 字段

const FS = require("fs");
const TASKS = "/home/admin/openclaw/workspace/stock-assistant/tasks";
const PORTAL_TASKS = "/home/admin/openclaw/workspace/portal/status/tasks.json";

function parseFrontmatter(content) {
    // 提取 --- --- 之间的 YAML frontmatter
    const match = content.match(/^---\n([\s\S]*?)\n---/);
    if (!match) return {};
    const yaml = match[1];
    const result = {};
    yaml.split("\n").forEach(line => {
        const idx = line.indexOf(":");
        if (idx === -1) return;
        const key = line.slice(0, idx).trim();
        const val = line.slice(idx + 1).trim();
        if (key) result[key] = val;
    });
    return result;
}

function scanDir(dir) {
    if (!FS.existsSync(dir)) return [];
    const files = FS.readdirSync(dir)
        .filter(f => f.endsWith(".md") || f.endsWith(".running"));
    return files.map(f => {
        const path = `${dir}/${f}`;
        const raw = FS.readFileSync(path, "utf8");
        const id = f.replace(/\.(md|running)$/, "");
        const fm = parseFrontmatter(raw);
        const meta = {
            id,
            file: f,
            modified: FS.statSync(path).mtime.toISOString()
        };
        // 提取常用字段
        if (fm.status) meta.status = fm.status;
        if (fm.agent) meta.agent = fm.agent;
        if (fm.priority) meta.priority = fm.priority;
        if (fm.created) meta.created = fm.created;
        if (fm.updated) meta.updated = fm.updated;
        return meta;
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
    console.error(`[snapshot] generated: todo=${snap.todo.length} doing=${snap.doing.length} done=${snap.done.length} lastUpdated=${snap.lastUpdated}`);
    return snap;
}

generate();
