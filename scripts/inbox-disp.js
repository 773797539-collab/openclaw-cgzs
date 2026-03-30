#!/usr/env node
'use strict';
const FS   = require('fs');
const PATH = require('path');

// ===== 路径 =====
const DONE_DIR  = '/home/admin/openclaw/workspace/stock-assistant/tasks/done';
const TODO_DIR  = '/home/admin/openclaw/workspace/stock-assistant/tasks/todo';
const DOING_DIR = '/home/admin/openclaw/workspace/stock-assistant/tasks/doing';
const INBOX_DIR = '/home/admin/openclaw/workspace/stock-assistant/tasks/inbox';

// ===== 任务模板（严格 P0→P1→P2→P3）=====
const TEMPLATES = [
    // ========== P0: 股票主业务 ==========
    { id:'持仓扫描-',        type:'持仓扫描',      agent:'stock-main', priority:'P0' },
    { id:'持仓风险更新-',   type:'持仓风险更新',   agent:'stock-main', priority:'P0' },
    { id:'观察池扫描-',      type:'观察池扫描',     agent:'stock-main', priority:'P0' },
    { id:'观察池迁移-',     type:'观察池迁移',     agent:'stock-main', priority:'P0' },
    { id:'剔除原因回填-',   type:'剔除原因回填',   agent:'stock-main', priority:'P0' },
    { id:'市场环境判断-',   type:'市场环境判断',   agent:'stock-main', priority:'P0' },
    { id:'热点板块-',        type:'热点板块',        agent:'stock-main', priority:'P0' },
    { id:'持仓重点-',        type:'持仓重点',        agent:'stock-main', priority:'P0' },
    { id:'今日重点3股-',    type:'今日重点3股',    agent:'stock-main', priority:'P0' },
    { id:'风险提醒-',        type:'风险提醒',        agent:'stock-main', priority:'P0' },
    { id:'行动计划-',        type:'行动计划',        agent:'stock-main', priority:'P0' },
    { id:'异动监控-',        type:'异动监控',        agent:'stock-main', priority:'P0' },
    { id:'公告变化-',        type:'公告变化',        agent:'stock-main', priority:'P0' },
    { id:'环境切换-',        type:'环境切换',        agent:'stock-main', priority:'P0' },
    { id:'强时效提醒-',      type:'强时效提醒',      agent:'stock-main', priority:'P0' },
    { id:'市场复盘-',        type:'市场复盘',        agent:'stock-main', priority:'P0' },
    { id:'持仓复盘-',        type:'持仓复盘',        agent:'stock-main', priority:'P0' },
    { id:'选股复盘-',        type:'选股复盘',        agent:'stock-main', priority:'P0' },
    { id:'错误归因-',        type:'错误归因',        agent:'stock-main', priority:'P0' },
    { id:'次日准备-',        type:'次日准备',        agent:'stock-main', priority:'P0' },
    { id:'holdings更新-',  type:'holdings更新',   agent:'stock-main', priority:'P0' },
    { id:'watchlist更新-', type:'watchlist更新',  agent:'stock-main', priority:'P0' },
    { id:'related记录-',   type:'related记录',    agent:'stock-main', priority:'P0' },
    { id:'recent扫描-',    type:'recent扫描',     agent:'stock-main', priority:'P0' },
    // ========== P1: 股票系统成长 ==========
    { id:'skill调研-',       type:'skill调研',       agent:'stock-main', priority:'P1' },
    { id:'workflow优化-',  type:'workflow优化',    agent:'stock-main', priority:'P1' },
    { id:'失败样本沉淀-',   type:'失败样本沉淀',     agent:'stock-main', priority:'P1' },
    { id:'规则提炼-',        type:'规则提炼',        agent:'stock-main', priority:'P1' },
    { id:'MEMORY检查-',     type:'MEMORY检查',      agent:'stock-main', priority:'P1' },
    { id:'股票规律沉淀-',   type:'股票规律沉淀',     agent:'stock-main', priority:'P1' },
    { id:'市场模式沉淀-',   type:'市场模式沉淀',     agent:'stock-main', priority:'P1' },
    { id:'通知规则优化-',   type:'通知规则优化',     agent:'stock-main', priority:'P1' },
    // ========== P2: 门户站优化 ==========
    { id:'asset-center优化-', type:'asset-center优化', agent:'stock-main', priority:'P2' },
    { id:'状态页中文化-',    type:'状态页中文化',    agent:'stock-main', priority:'P2' },
    { id:'详情预览统一-',    type:'详情预览统一',    agent:'stock-main', priority:'P2' },
    { id:'局部刷新优化-',    type:'局部刷新优化',    agent:'stock-main', priority:'P2' },
    { id:'资产观察池一致性-',type:'资产观察池一致性',agent:'stock-main', priority:'P2' },
    { id:'高价值产出过滤-',  type:'高价值产出过滤',  agent:'stock-main', priority:'P2' },
    // ========== P3: 最低兜底 ==========
    { id:'sys-diag-',        type:'diagnostic',  agent:'system', priority:'P3' },
    { id:'sys-consistency-', type:'consistency', agent:'system', priority:'P3' },
    { id:'脏任务归档-',       type:'脏任务归档',   agent:'system', priority:'P3' },
    { id:'异常日志整理-',     type:'异常日志整理', agent:'system', priority:'P3' },
];

// ===== 轮转状态 =====
const STATE_FILE = '/tmp/inbox-disp-state.json';
function loadState() {
    try {
        if (FS.existsSync(STATE_FILE)) return JSON.parse(FS.readFileSync(STATE_FILE, 'utf8'));
    } catch {}
    return { p0Idx: 0, p1Idx: 0, p2Idx: 0 };
}
function saveState(s) {
    FS.writeFileSync(STATE_FILE, JSON.stringify(s));
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

// ===== 去重：某类型最近 N 毫秒内完成过 =====
function recentDone(type, windowMs) {
    if (!FS.existsSync(DONE_DIR)) return false;
    const files = FS.readdirSync(DONE_DIR).filter(f => f.startsWith(type));
    if (files.length === 0) return false;
    const latest = files.sort().pop();
    const mtime  = FS.statSync(PATH.join(DONE_DIR, latest)).mtimeMs;
    return (Date.now() - mtime) < windowMs;
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

// ===== 选择模板（加去重）=====
function selectTemplate() {
    const counts = countByPriority(TODO_DIR);
    const state  = loadState();

    // ===== 持仓/观察池核心任务：5 分钟冷却 =====
    const CORE_COOL = 5 * 60 * 1000;
    // ===== 其他 P0 任务：30 分钟冷却 =====
    const P0_COOL   = 30 * 60 * 1000;
    // ===== P1/P2：2 小时冷却 =====
    const P12_COOL  = 2 * 60 * 60 * 1000;

    // === P0 永远维持至少 2 个 ===
    if (counts.P0 < 2) {
        const p0Templates = TEMPLATES.filter(t => t.priority === 'P0');
        for (let offset = 1; offset <= p0Templates.length; offset++) {
            const idx = (state.p0Idx + offset) % p0Templates.length;
            const tpl = p0Templates[idx];
            const cool = (tpl.type === '持仓扫描' || tpl.type === '持仓风险更新'
                        || tpl.type === '观察池扫描' || tpl.type === 'watchlist更新'
                        || tpl.type === 'holdings更新' || tpl.type === 'recent扫描')
                       ? CORE_COOL : P0_COOL;
            if (!recentDone(tpl.id, cool)) {
                saveState({ ...state, p0Idx: idx });
                return tpl;
            }
        }
        return null; // 所有 P0 都在冷却中
    }

    // === P0 ≥ 2，补充 P1/P2 ===
    if (counts.total < 3) {
        for (let offset = 1; offset <= TEMPLATES.length; offset++) {
            const idx = (state.p1Idx + offset) % TEMPLATES.length;
            const tpl = TEMPLATES[idx];
            if (tpl.priority === 'P0') continue;
            if (tpl.priority === 'P3') continue;
            const cool = (tpl.priority === 'P1') ? P12_COOL : P12_COOL;
            if (!recentDone(tpl.id, cool)) {
                saveState({ ...state, p1Idx: idx, p2Idx: idx });
                return tpl;
            }
        }
    }

    // === 只有 P0/P1/P2 都没有才做 P3 ===
    if (counts.P0 === 0 && counts.P1 === 0 && counts.P2 === 0) {
        const tpl = TEMPLATES.find(t => t.priority === 'P3');
        if (tpl && !recentDone(tpl.id, P12_COOL)) return tpl;
    }

    return null; // 都在冷却中
}

// ===== 核心调度 =====
function check_and_dispatch() {
    mkdir(TODO_DIR);
    mkdir(DOING_DIR);
    mkdir(INBOX_DIR);

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

    // 次优：replenish
    const tpl = selectTemplate();
    if (!tpl) return { action:'idle', reason:'all_in_cooldown', counts: countByPriority(TODO_DIR) };

    const taskId = tpl.id + nowTs();
    writeTask(tpl, taskId);
    return { action:'replenished', taskId, type:tpl.type, priority:tpl.priority, counts: countByPriority(TODO_DIR) };
}

// ===== 直接运行 =====
const result = check_and_dispatch();
console.log(JSON.stringify(result));
process.exit(0);
