#!/usr/bin/env node
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
    { id:'持仓风险更新-',    type:'持仓风险更新',   agent:'stock-main', priority:'P0' },
    { id:'观察池扫描-',      type:'观察池扫描',     agent:'stock-main', priority:'P0' },
    { id:'观察池迁移-',      type:'观察池迁移',     agent:'stock-main', priority:'P0' },
    { id:'剔除原因回填-',    type:'剔除原因回填',   agent:'stock-main', priority:'P0' },
    { id:'市场环境判断-',    type:'市场环境判断',   agent:'stock-main', priority:'P0' },
    { id:'热点板块-',        type:'热点板块',        agent:'stock-main', priority:'P0' },
    { id:'持仓重点-',        type:'持仓重点',        agent:'stock-main', priority:'P0' },
    { id:'今日重点3股-',     type:'今日重点3股',    agent:'stock-main', priority:'P0' },
    { id:'风险提醒-',        type:'风险提醒',        agent:'stock-main', priority:'P0' },
    { id:'行动计划-',         type:'行动计划',        agent:'stock-main', priority:'P0' },
    { id:'异动监控-',        type:'异动监控',        agent:'stock-main', priority:'P0' },
    { id:'公告变化-',        type:'公告变化',        agent:'stock-main', priority:'P0' },
    { id:'环境切换-',        type:'环境切换',        agent:'stock-main', priority:'P0' },
    { id:'强时效提醒-',      type:'强时效提醒',      agent:'stock-main', priority:'P0' },
    { id:'市场复盘-',        type:'市场复盘',        agent:'stock-main', priority:'P0' },
    { id:'持仓复盘-',        type:'持仓复盘',        agent:'stock-main', priority:'P0' },
    { id:'选股复盘-',        type:'选股复盘',        agent:'stock-main', priority:'P0' },
    { id:'错误归因-',        type:'错误归因',        agent:'stock-main', priority:'P0' },
    { id:'次日准备-',        type:'次日准备',        agent:'stock-main', priority:'P0' },
    { id:'holdings更新-',   type:'holdings更新',   agent:'stock-main', priority:'P0' },
    { id:'watchlist更新-',  type:'watchlist更新',  agent:'stock-main', priority:'P0' },
    { id:'related记录-',    type:'related记录',    agent:'stock-main', priority:'P0' },
    { id:'recent扫描-',     type:'recent扫描',     agent:'stock-main', priority:'P0' },
    // ========== P1: 股票系统成长 ==========
    { id:'skill调研-',       type:'skill调研',       agent:'stock-main', priority:'P1' },
    { id:'workflow优化-',   type:'workflow优化',    agent:'stock-main', priority:'P1' },
    { id:'失败样本沉淀-',   type:'失败样本沉淀',     agent:'stock-main', priority:'P1' },
    { id:'规则提炼-',        type:'规则提炼',        agent:'stock-main', priority:'P1' },
    { id:'MEMORY检查-',     type:'MEMORY检查',      agent:'stock-main', priority:'P1' },
    { id:'股票规律沉淀-',   type:'股票规律沉淀',     agent:'stock-main', priority:'P1' },
    { id:'市场模式沉淀-',   type:'市场模式沉淀',     agent:'stock-main', priority:'P1' },
    { id:'通知规则优化-',   type:'通知规则优化',     agent:'stock-main', priority:'P1' },
    // ========== P2: 门户站优化 ==========
    { id:'asset-center优化-',   type:'asset-center优化',  agent:'stock-main', priority:'P2' },
    { id:'状态页中文化-',       type:'状态页中文化',       agent:'stock-main', priority:'P2' },
    { id:'详情预览统一-',       type:'详情预览统一',       agent:'stock-main', priority:'P2' },
    { id:'局部刷新优化-',       type:'局部刷新优化',       agent:'stock-main', priority:'P2' },
    { id:'资产观察池一致性-',   type:'资产观察池一致性',   agent:'stock-main', priority:'P2' },
    { id:'高价值产出过滤-',     type:'高价值产出过滤',     agent:'stock-main', priority:'P2' },
    // ========== P3: 最低兜底 ==========
    { id:'sys-diag-',        type:'diagnostic',  agent:'system', priority:'P3' },
    { id:'sys-consistency-', type:'consistency', agent:'system', priority:'P3' },
    { id:'脏任务归档-',      type:'脏任务归档',   agent:'system', priority:'P3' },
    { id:'异常日志整理-',    type:'异常日志整理', agent:'system', priority:'P3' },
];

// ===== 轮转状态 =====
const STATE_FILE = '/tmp/inbox-disp-state.json';
function loadState() {
    try {
        if (FS.existsSync(STATE_FILE)) return JSON.parse(FS.readFileSync(STATE_FILE, 'utf8'));
    } catch {}
    return { p0Idx: 0, p1Idx: 0, p2Idx: 0, lastTime: 0 };
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

// ===== 选择模板（轮转，永远不重复上一个）=====
function selectTemplate() {
    const counts = countByPriority(TODO_DIR);
    const state  = loadState();
    const hour   = new Date().getHours();
    const minute = new Date().getMinutes();

    // 时间分段优先级
    const timeOrder = [];
    if (hour === 9 && minute < 30) timeOrder.push('市场环境判断');
    if (hour >= 9 && hour < 15)    timeOrder.push('异动监控', '公告变化', '环境切换', '强时效提醒');
    if (hour >= 15 && hour < 16)   timeOrder.push('市场复盘', '持仓复盘', '选股复盘', '错误归因', '次日准备');

    const regularOrder = ['持仓扫描','观察池扫描','持仓风险更新','持仓重点',
                          '热点板块','今日重点3股','风险提醒','行动计划',
                          'holdings更新','watchlist更新','related记录','recent扫描',
                          '观察池迁移','剔除原因回填'];

    const orderedTypes = [...new Set([...timeOrder, ...regularOrder])];

    // === P0 永远维持至少 2 个 ===
    if (counts.P0 < 2) {
        const p0Templates = TEMPLATES.filter(t => t.priority === 'P0');
        if (p0Templates.length === 0) return null;

        // 优先选时间分段+常规顺序中，下一个非"持仓扫描"的P0
        // 从 lastIdx+1 开始轮转
        let idx = (state.p0Idx + 1) % p0Templates.length;
        let attempts = 0;
        while (attempts < p0Templates.length) {
            const tpl = p0Templates[idx];
            attempts++;
            idx = (idx + 1) % p0Templates.length;
            // 跳过"持仓扫描"（优先级最低的兜底）
            if (tpl.type === '持仓扫描') {
                // 把它放到轮转末尾，下次再跳过
                continue;
            }
            // 优先选时间/常规顺序靠前的
            const typePos = orderedTypes.indexOf(tpl.type);
            if (typePos !== -1 || tpl.type !== '持仓扫描') {
                saveState({ ...state, p0Idx: idx });
                return tpl;
            }
        }
        // 兜底：跳过持仓扫描，选下一个
        const safeIdx = (state.p0Idx + 2) % p0Templates.length;
        saveState({ ...state, p0Idx: safeIdx });
        return p0Templates[safeIdx] || p0Templates[0];
    }

    // === P0 ≥ 2，补充 P1/P2 ===
    if (counts.total < 3) {
        const p1Templates = TEMPLATES.filter(t => t.priority === 'P1');
        if (p1Templates.length > 0) {
            const idx = (state.p1Idx + 1) % p1Templates.length;
            saveState({ ...state, p1Idx: idx });
            return p1Templates[idx];
        }
        const p2Templates = TEMPLATES.filter(t => t.priority === 'P2');
        if (p2Templates.length > 0) {
            const idx = (state.p2Idx + 1) % p2Templates.length;
            saveState({ ...state, p2Idx: idx });
            return p2Templates[idx];
        }
    }

    // === 只有 P0/P1/P2 都没有才做 P3 ===
    if (counts.P0 === 0 && counts.P1 === 0 && counts.P2 === 0) {
        const tpl = TEMPLATES.find(t => t.priority === 'P3');
        if (tpl) return tpl;
    }

    return null;
}

// ===== 核心调度 =====
function check_and_dispatch() {
    mkdir(TODO_DIR);
    mkdir(DOING_DIR);
    mkdir(INBOX_DIR);

    // 优先：dispatch 一个已有 todo → doing
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

    // 次优：todo 为空 → replenish
    const tpl = selectTemplate();
    if (!tpl) return { action:'idle', reason:'no_candidate', counts: countByPriority(TODO_DIR) };

    const taskId = tpl.id + nowTs();
    writeTask(tpl, taskId);
    return { action:'replenished', taskId, type:tpl.type, priority:tpl.priority, counts: countByPriority(TODO_DIR) };
}

// ===== 直接运行 =====
const result = check_and_dispatch();
console.log(JSON.stringify(result));
process.exit(0);
