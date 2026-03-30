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
    // 持仓
    { id:'持仓扫描-',        type:'持仓扫描',      agent:'stock-main', priority:'P0', minInterval:3600  },
    { id:'持仓风险更新-',    type:'持仓风险更新',   agent:'stock-main', priority:'P0', minInterval:3600  },
    // 观察池
    { id:'观察池扫描-',      type:'观察池扫描',     agent:'stock-main', priority:'P0', minInterval:3600  },
    { id:'观察池迁移-',      type:'观察池迁移',     agent:'stock-main', priority:'P0', minInterval:7200  },
    { id:'剔除原因回填-',    type:'剔除原因回填',   agent:'stock-main', priority:'P0', minInterval:7200  },
    // 盘前（09:00-09:30）
    { id:'市场环境判断-',    type:'市场环境判断',   agent:'stock-main', priority:'P0', minInterval:43200 },
    { id:'热点板块-',        type:'热点板块',        agent:'stock-main', priority:'P0', minInterval:43200 },
    { id:'持仓重点-',        type:'持仓重点',        agent:'stock-main', priority:'P0', minInterval:43200 },
    { id:'今日重点3股-',     type:'今日重点3股',    agent:'stock-main', priority:'P0', minInterval:43200 },
    { id:'风险提醒-',        type:'风险提醒',        agent:'stock-main', priority:'P0', minInterval:43200 },
    { id:'行动计划-',         type:'行动计划',        agent:'stock-main', priority:'P0', minInterval:43200 },
    // 盘中（09:30-15:00）
    { id:'异动监控-',        type:'异动监控',        agent:'stock-main', priority:'P0', minInterval:1800  },
    { id:'公告变化-',        type:'公告变化',        agent:'stock-main', priority:'P0', minInterval:3600  },
    { id:'环境切换-',        type:'环境切换',        agent:'stock-main', priority:'P0', minInterval:7200  },
    { id:'强时效提醒-',      type:'强时效提醒',      agent:'stock-main', priority:'P0', minInterval:3600  },
    // 盘后（15:00-16:00）
    { id:'市场复盘-',        type:'市场复盘',        agent:'stock-main', priority:'P0', minInterval:43200 },
    { id:'持仓复盘-',        type:'持仓复盘',        agent:'stock-main', priority:'P0', minInterval:43200 },
    { id:'选股复盘-',        type:'选股复盘',        agent:'stock-main', priority:'P0', minInterval:43200 },
    { id:'错误归因-',        type:'错误归因',        agent:'stock-main', priority:'P0', minInterval:43200 },
    { id:'次日准备-',        type:'次日准备',        agent:'stock-main', priority:'P0', minInterval:43200 },
    // 资产中心
    { id:'holdings更新-',   type:'holdings更新',   agent:'stock-main', priority:'P0', minInterval:3600  },
    { id:'watchlist更新-',  type:'watchlist更新',  agent:'stock-main', priority:'P0', minInterval:7200  },
    { id:'related记录-',    type:'related记录',    agent:'stock-main', priority:'P0', minInterval:7200  },
    { id:'recent扫描-',     type:'recent扫描',     agent:'stock-main', priority:'P0', minInterval:7200  },

    // ========== P1: 股票系统成长 ==========
    { id:'skill调研-',       type:'skill调研',       agent:'stock-main', priority:'P1', minInterval:86400 },
    { id:'workflow优化-',   type:'workflow优化',    agent:'stock-main', priority:'P1', minInterval:86400 },
    { id:'失败样本沉淀-',   type:'失败样本沉淀',     agent:'stock-main', priority:'P1', minInterval:21600 },
    { id:'规则提炼-',        type:'规则提炼',        agent:'stock-main', priority:'P1', minInterval:86400 },
    { id:'MEMORY检查-',     type:'MEMORY检查',      agent:'stock-main', priority:'P1', minInterval:86400 },
    { id:'股票规律沉淀-',   type:'股票规律沉淀',     agent:'stock-main', priority:'P1', minInterval:86400 },
    { id:'市场模式沉淀-',   type:'市场模式沉淀',     agent:'stock-main', priority:'P1', minInterval:86400 },
    { id:'通知规则优化-',   type:'通知规则优化',     agent:'stock-main', priority:'P1', minInterval:86400 },

    // ========== P2: 门户站优化 ==========
    { id:'asset-center优化-',   type:'asset-center优化',  agent:'stock-main', priority:'P2', minInterval:86400 },
    { id:'状态页中文化-',       type:'状态页中文化',       agent:'stock-main', priority:'P2', minInterval:86400 },
    { id:'详情预览统一-',       type:'详情预览统一',       agent:'stock-main', priority:'P2', minInterval:86400 },
    { id:'局部刷新优化-',       type:'局部刷新优化',       agent:'stock-main', priority:'P2', minInterval:86400 },
    { id:'资产观察池一致性-',   type:'资产观察池一致性',   agent:'stock-main', priority:'P2', minInterval:86400 },
    { id:'高价值产出过滤-',     type:'高价值产出过滤',     agent:'stock-main', priority:'P2', minInterval:86400 },

    // ========== P3: 最低兜底 ==========
    { id:'sys-diag-',        type:'diagnostic',  agent:'system', priority:'P3', minInterval:7200  },
    { id:'sys-consistency-', type:'consistency', agent:'system', priority:'P3', minInterval:7200  },
    { id:'脏任务归档-',      type:'脏任务归档',   agent:'system', priority:'P3', minInterval:14400 },
    { id:'异常日志整理-',    type:'异常日志整理', agent:'system', priority:'P3', minInterval:14400 },
];

// ===== 工具 =====
function nowTs()    { return Date.now(); }
function getDateStr() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
}

function recentDoneCount(taskPrefix, intervalSec) {
    if (!FS.existsSync(DONE_DIR)) return 0;
    const cutoff = nowTs() - intervalSec * 1000;
    return FS.readdirSync(DONE_DIR)
        .filter(f => f.startsWith(taskPrefix) && f.endsWith('.md'))
        .filter(f => FS.statSync(PATH.join(DONE_DIR, f)).mtimeMs > cutoff)
        .length;
}

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

function mkdir(dir) { FS.mkdirSync(dir, {recursive:true}); }

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

// ===== 选择最优先模板（严格 P0→P1→P2→P3）=====
function selectTemplate() {
    const counts = countByPriority(TODO_DIR);
    const hour   = new Date().getHours();
    const minute = new Date().getMinutes();

    // === 规则1: P0 永远维持至少 2 个 ===
    if (counts.P0 < 2) {
        // P0=0 时极度饥饿：忽略 minInterval，直接找任意 P0 模板
        const p0Templates = TEMPLATES.filter(t => t.priority === 'P0');
        if (counts.P0 === 0) {
            // 找任意 P0（不管 minInterval）
            const candidates = [
                p0Templates.find(t => t.id === '持仓扫描-'),
                p0Templates.find(t => t.id === '观察池扫描-'),
                p0Templates.find(t => t.id === '异动监控-'),
                p0Templates.find(t => t.id === '持仓风险更新-'),
            ].filter(Boolean);
            for (const tpl of candidates) return tpl;
            // 兜底：任意 P0
            for (const tpl of p0Templates) return tpl;
        }
        // P0=1：尝试找新的 P0（minInterval 约束）
        if (hour === 9 && minute < 30) {
            const tpl = p0Templates.find(t => t.id === '市场环境判断-');
            if (tpl && recentDoneCount(tpl.id, tpl.minInterval) === 0) return tpl;
        }
        if (hour >= 9 && hour < 15) {
            const tpl = p0Templates.find(t => t.id === '异动监控-');
            if (tpl && recentDoneCount(tpl.id, tpl.minInterval) === 0) return tpl;
        }
        if (hour >= 15 && hour < 16) {
            const tpl = p0Templates.find(t => t.id === '市场复盘-');
            if (tpl && recentDoneCount(tpl.id, tpl.minInterval) === 0) return tpl;
        }
        const candidates = [
            p0Templates.find(t => t.id === '持仓扫描-'),
            p0Templates.find(t => t.id === '观察池扫描-'),
            p0Templates.find(t => t.id === '持仓风险更新-'),
        ].filter(Boolean);
        for (const tpl of candidates) {
            if (recentDoneCount(tpl.id, tpl.minInterval) === 0) return tpl;
        }
        // 兜底：任意 minInterval 已过的 P0
        for (const tpl of p0Templates) {
            if (recentDoneCount(tpl.id, tpl.minInterval) === 0) return tpl;
        }
        // 如果找不到可补的 P0，先补 P1（不做 P0 饿死时的硬阻塞）
    }

    // === 规则2: P0 ≥ 2，但 todo 总数 < 3 → 补 P1/P2 ===
    if (counts.total < 3) {
        for (const pri of ['P1', 'P2']) {
            for (const tpl of TEMPLATES.filter(t => t.priority === pri)) {
                if (recentDoneCount(tpl.id, tpl.minInterval) === 0) return tpl;
            }
        }
    }

    // === 规则3: P0 ≥ 2 且 P1/P2 已满，才允许 P3 ===
    if (counts.P0 >= 2 && counts.total < 3) {
        for (const tpl of TEMPLATES.filter(t => t.priority === 'P3')) {
            if (recentDoneCount(tpl.id, tpl.minInterval) === 0) return tpl;
        }
    }

    return null; // 充分条件未满足，不补货
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

    // 次优：todo 为空或 P0 不足 → replenish
    // 注意：P0<2 时即使 total>=3 也要补（P0 永远优先）
    const counts = countByPriority(TODO_DIR);
    const tpl = selectTemplate();
    if (!tpl) return { action:'idle', reason:'no_candidate', counts };

    const taskId = tpl.id + nowTs();
    writeTask(tpl, taskId);
    return { action:'replenished', taskId, type:tpl.type, priority:tpl.priority, counts };
}

// ===== 直接运行 =====
const result = check_and_dispatch();
console.log(JSON.stringify(result));
process.exit(0);
