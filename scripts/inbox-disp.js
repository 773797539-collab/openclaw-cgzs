#!/usr/bin/env node
'use strict';
const FS   = require('fs');
const PATH = require('path');

// ===== 路径 =====
const DONE_DIR  = '/home/admin/openclaw/workspace/stock-assistant/tasks/done';
const TODO_DIR  = '/home/admin/openclaw/workspace/stock-assistant/tasks/todo';
const DOING_DIR = '/home/admin/openclaw/workspace/stock-assistant/tasks/doing';

// ===== 主执行链白名单（只有这些任务才允许进入执行链）=====
const CORE_TEMPLATES = [
    { id:'持仓扫描-',       type:'持仓扫描',       agent:'stock-main', priority:'P0' },
    { id:'持仓风险更新-',  type:'持仓风险更新',   agent:'stock-main', priority:'P0' },
    { id:'观察池扫描-',    type:'观察池扫描',     agent:'stock-main', priority:'P0' },
    { id:'holdings更新-', type:'holdings更新',   agent:'stock-main', priority:'P0' },
    { id:'watchlist更新-',type:'watchlist更新',  agent:'stock-main', priority:'P0' },
];

// ===== 轮转状态 =====
const STATE_FILE = '/tmp/inbox-disp-state.json';
function loadState() {
    try {
        if (FS.existsSync(STATE_FILE)) {
            const s = JSON.parse(FS.readFileSync(STATE_FILE, 'utf8'));
            // 安全检查：coreIdx 必须在 [0, CORE_TEMPLATES.length-1] 范围内
            if (typeof s.coreIdx === 'number' && s.coreIdx >= 0 && s.coreIdx < CORE_TEMPLATES.length) {
                return s;
            }
        }
    } catch {}
    return { coreIdx: 0 };
}
function saveState(s) {
    try {
        FS.writeFileSync(STATE_FILE, JSON.stringify(s));
    } catch(e) {
        console.error('saveState failed:', e.message);
    }
}

// ===== 工具 =====
function nowTs() { return Date.now(); }
function mkdir(dir) { FS.mkdirSync(dir, {recursive:true}); }

function countByPriority(dir) {
    const c = { P0:0, P1:0, P2:0, P3:0, total:0 };
    if (!FS.existsSync(dir)) return c;
    for (const f of FS.readdirSync(dir)) {
        if (!f.endsWith('.md')) continue;
        const m = FS.readFileSync(PATH.join(dir, f), 'utf8').match(/priority:\s*'(P[0-3])'/);
        const p = m ? m[1] : 'P3';
        if (p in c) c[p]++;
        c.total++;
    }
    return c;
}

// ===== 去重：核心任务 5 分钟冷却 =====
const CORE_COOL_MS = 5 * 60 * 1000;

function recentDone(typePrefix) {
    if (!FS.existsSync(DONE_DIR)) return false;
    const files = FS.readdirSync(DONE_DIR).filter(f => f.startsWith(typePrefix));
    if (files.length === 0) return false;
    const latest = files.sort().pop();
    const mtime  = FS.statSync(PATH.join(DONE_DIR, latest)).mtimeMs;
    return (Date.now() - mtime) < CORE_COOL_MS;
}

// ===== 写任务文件 =====
function writeTask(tpl, taskId) {
    mkdir(TODO_DIR);
    const fp = PATH.join(TODO_DIR, taskId + '.md');
    FS.writeFileSync(fp, `---
id: ${taskId}
type: ${tpl.type}
agent: ${tpl.agent}
priority: '${tpl.priority}'
created: ${new Date().toISOString()}
status: pending
---
# ${tpl.type}

*priority: ${tpl.priority} | agent: ${tpl.agent}*
`);
    return fp;
}

// ===== 核心调度：只选白名单任务 =====
function check_and_dispatch() {
    mkdir(TODO_DIR);
    mkdir(DOING_DIR);

    // 优先：dispatch 已有 todo → doing
    const todoFiles = FS.readdirSync(TODO_DIR).filter(f => f.endsWith('.md')).sort();
    if (todoFiles.length > 0) {
        const taskFile = todoFiles[0];
        const taskId   = taskFile.replace('.md','');
        const src = PATH.join(TODO_DIR, taskFile);
        const dst = PATH.join(DOING_DIR, taskFile);
        try {
            FS.renameSync(src, dst);
            FS.writeFileSync(PATH.join(DOING_DIR, taskId + '.running'), String(nowTs()));
            return { action:'dispatched', taskId, dispatchedBy:'inbox-disp' };
        } catch(e) {
            return { action:'error', error: e.message };
        }
    }

    // replenish：从白名单轮转选一个（跳过冷却中的）
    const state = loadState();
    const len = CORE_TEMPLATES.length;
    for (let offset = 1; offset <= len; offset++) {
        const idx = (state.coreIdx + offset) % len;
        const tpl = CORE_TEMPLATES[idx];
        if (!tpl) continue;
        if (!recentDone(tpl.id)) {
            saveState({ coreIdx: idx });
            const taskId = tpl.id + nowTs();
            writeTask(tpl, taskId);
            return { action:'replenished', taskId, type:tpl.type, priority:tpl.priority, counts: countByPriority(TODO_DIR) };
        }
    }

    // 全部在冷却中，idle
    return { action:'idle', reason:'all_in_cooldown', counts: countByPriority(TODO_DIR) };
}

// ===== 直接运行 =====
const result = check_and_dispatch();
console.log(JSON.stringify(result));
process.exit(0);
