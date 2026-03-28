/* OpenClaw Portal v11 */
var REFRESH = 10;
var countdown = REFRESH;
var timer;

async function fetchAll() {
  try { var r = await fetch('/api/status/all'); var d = await r.json(); renderAll(d); }
  catch (e) { console.error('fetch error', e); }
}

function renderAll(d) {
  renderGovernance(d.governance || d.system || {});
  renderTasks(d.tasks || {});
  renderApprovals(d.approvals || {});
  renderBlockers(d.blockers || {});
  renderRecentResults(d.recent_results || {});
  renderRecentExceptions(d.recent_exceptions || {});
  renderPortfolio(d.portfolio || {});
  renderBackupHealth(d.backup_health || {});
  renderMemoryHealth(d.memory_health || {});
  renderChangelog(d.changelog_summary || d.changelog || []);
  renderAgentArchitecture(d.agent_architecture || {});
  renderMultiProject(d.multi_project || {});
  bindTaskClicks();
  startCountdown();
}

function escHtml(s) {
  if (s == null) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function fmtNum(n) { return Math.round(n).toLocaleString('zh-CN'); }

function renderGovernance(g) {
  if (!g) return;
  function setEl(id, val) { var e = document.getElementById(id); if (e) e.textContent = val; }
  setEl('gov-version', g.version || g.oc_version || '-');
  setEl('gov-model', g.current_model || g.model || '-');
  setEl('gov-agent-count', String(g.agent_count || (g.agents && g.agents.length) || '0'));
  setEl('gov-backup-time', g.backup_time || g.last_backup || '-');
  setEl('gov-project', g.current_project || g.project || '-');
  setEl('gov-channel', g.current_channel || g.channel || '-');
  var gwDot = document.getElementById('gov-gateway-dot');
  if (gwDot) gwDot.className = 'dot ' + (g.gateway_status==='running' ? 'dot-green' : 'dot-red');
  setEl('gov-gateway-status', g.gateway_status==='running' ? '运行中' : (g.gateway_status || '-'));
}

function renderTasks(t) {
  if (!t) return;
  var panels = [{id:'todo-list',key:'todo'},{id:'doing-list',key:'doing'},{id:'done-list',key:'done'},{id:'blocked-list',key:'blocked'}];
  panels.forEach(function(p) {
    var el = document.getElementById(p.id); if (!el) return;
    var items = t[p.key] || [];
    el.innerHTML = items.length ? items.map(renderTaskItem).join('') : '<div style="color:var(--text2);font-size:12px;padding:8px">暂无任务</div>';
    var badge = document.getElementById(p.id.replace('-list','-count')); if (badge) badge.textContent = items.length;
  });
  var doneEl = document.getElementById('task-done-count'); if (doneEl) doneEl.textContent = (t.done||[]).length;
}

function renderTaskItem(task) {
  var title = escHtml(task.name||'');
  var execAgent = escHtml(task.exec_agent||'-');
  var reviewAgent = escHtml(task.review_agent||'-');
  var date = escHtml(task.date||'');
  var taskId = escHtml(task.task_id||'-');
  var gitCommit = escHtml(task.git_commit||'-');
  var reviewStatus = escHtml(task.review_status||task.status||'-');
  var reviewSummary = escHtml(task.review_summary||'-');
  var docSync = escHtml(task.doc_sync||'-');
  var blocker = escHtml(task.blocker_reason||'');
  var reviewTime = escHtml(task.review_time||date);
  var statusColor = reviewStatus==='通过'?'green':reviewStatus==='进行中'?'blue':reviewStatus==='待验收'?'orange':'gray';
  var taskIdTag = taskId!=='-' ? '<span class="task-id">'+taskId.replace('TASK-','')+'</span>' : '';
  var hasDetail = reviewSummary!=='-' || gitCommit!=='-' || docSync!=='-';
  var detailHtml = '';
  if (hasDetail || blocker) {
    detailHtml = '<div class="task-detail">' +
      '<div class="task-detail-row"><span class="task-detail-label">执行Agent</span><span>'+execAgent+'</span></div>' +
      '<div class="task-detail-row"><span class="task-detail-label">验收Agent</span><span>'+reviewAgent+' - '+reviewStatus+' - '+reviewTime+'</span></div>' +
      (reviewSummary!=='-' ? '<div class="task-detail-row"><span class="task-detail-label">验收摘要</span><span>'+reviewSummary+'</span></div>' : '') +
      (gitCommit!=='-' ? '<div class="task-detail-row"><span class="task-detail-label">Git提交</span><span style="font-family:var(--mono);font-size:9px">'+gitCommit.slice(0,8)+'</span></div>' : '') +
      (docSync!=='-' ? '<div class="task-detail-row"><span class="task-detail-label">文档同步</span><span>'+docSync+'</span></div>' : '') +
      (blocker ? '<div class="task-blocker">阻塞: '+blocker+'</div>' : '') + '</div>';
  }
  return '<div class="task-item"><div class="task-title">'+title+'</div><div class="task-meta">' +
    '<span class="task-type-tag" style="background:var(--'+statusColor+')">'+reviewStatus+'</span>' +
    (taskIdTag||'') + '<span style="color:var(--text2);font-size:9px">'+date+'</span></div>'+detailHtml+'</div>';
}

function bindTaskClicks() {
  document.querySelectorAll('.task-item').forEach(function(el) {
    el.style.cursor = 'pointer';
    el.onclick = function() { var d = el.querySelector('.task-detail'); if (d) d.classList.toggle('show'); };
  });
}

function renderApprovals(a) {
  var list = document.getElementById('approval-list');
  var countEl = document.getElementById('approval-count');
  if (!list) return;
  var count = (a && a.count) || 0;
  if (countEl) countEl.textContent = count + ' 项';
  if (!count) {
    list.innerHTML = '<div style="color:var(--text2);font-size:12px;padding:8px">暂无待审批<div style="font-size:10px;margin-top:4px">进入条件：需要人工确认的变更或决策</div></div>'; return;
  }
  var html = (a.approvals||[]).map(function(r) {
    return '<div class="task-item"><div class="task-title">'+escHtml(r.title||'')+'</div><div class="task-meta"><span style="color:var(--orange)">待审批</span></div><div class="task-detail">'+
      (r.submitted_by?'<div class="task-detail-row"><span class="task-detail-label">发起人</span><span>'+escHtml(r.submitted_by)+'</span></div>':'')+
      (r.impact?'<div class="task-detail-row"><span class="task-detail-label">影响范围</span><span>'+escHtml(r.impact)+'</span></div>':'')+
      (r.action_required?'<div class="task-detail-row"><span class="task-detail-label">所需操作</span><span>'+escHtml(r.action_required)+'</span></div>':'')+
    '</div></div>';
  }).join('');
  list.innerHTML = html;
}

function renderBlockers(b) {
  var list = document.getElementById('blocker-list');
  var countEl = document.getElementById('blocker-count');
  if (!list) return;
  var count = (b && b.count) || 0;
  if (countEl) countEl.textContent = count + ' 项';
  if (!count) {
    list.innerHTML = '<div style="color:var(--text2);font-size:12px;padding:8px">暂无阻塞<div style="font-size:10px;margin-top:4px">进入条件：任务缺少依赖或人工输入</div></div>'; return;
  }
  var html = (b.blockers||[]).map(function(r) {
    return '<div class="task-item"><div class="task-title">'+escHtml(r.title||'')+'</div><div class="task-meta"><span style="color:var(--red)">阻塞</span></div><div class="task-detail">'+
      (r.impact?'<div class="task-detail-row"><span class="task-detail-label">影响范围</span><span>'+escHtml(r.impact)+'</span></div>':'')+
      (r.workaround?'<div class="task-detail-row"><span class="task-detail-label">规避方案</span><span>'+escHtml(r.workaround)+'</span></div>':'')+
      (r.resolution?'<div class="task-detail-row"><span class="task-detail-label">所需输入</span><span>'+escHtml(r.resolution)+'</span></div>':'')+
    '</div></div>';
  }).join('');
  list.innerHTML = html;
}

function renderRecentResults(r) {
  var list = document.getElementById('result-list');
  var countEl = document.getElementById('result-count');
  if (!list) return;
  var results = (r && r.results) || [];
  if (countEl) countEl.textContent = results.length + ' 条';
  if (!results.length) { list.innerHTML = '<div style="color:var(--text2);font-size:12px;padding:8px">暂无最近结果</div>'; return; }
  var html = results.slice(0,10).map(function(i) {
    var gl = i.git_commit && i.git_commit!=='-' ? '<span class="task-id">'+i.git_commit.slice(0,8)+'</span>' : '';
    return '<div class="task-item"><div class="task-title">'+escHtml(i.name||i.task_name||'')+'</div><div class="task-meta"><span>'+escHtml(i.agent||'')+'</span><span style="color:var(--green)">通过</span>'+gl+'</div></div>';
  }).join('');
  list.innerHTML = html;
}

function renderRecentExceptions(e) {
  var list = document.getElementById('exception-list');
  var countEl = document.getElementById('exception-count');
  if (!list) return;
  var items = (e && e.exceptions) || [];
  if (countEl) countEl.textContent = items.length + ' 条';
  if (!items.length) { list.innerHTML = '<div style="color:var(--text2);font-size:12px;padding:8px">暂无最近异常</div>'; return; }
  var html = items.map(function(i) {
    var lc = i.level==='error'?'var(--red)':i.level==='warning'?'var(--orange)':'var(--text2)';
    return '<div class="task-item"><div class="task-title" style="font-size:12px;color:'+lc+'">'+escHtml(i.message||i.error||'')+'</div><div class="task-meta"><span style="font-size:9px">'+escHtml(i.time||'')+'</span></div></div>';
  }).join('');
  list.innerHTML = html;
}

function renderPortfolio(p) {
  if (!p) {
    var el = document.getElementById('holding-list');
    if(el) el.innerHTML='<div style="color:var(--text2);font-size:12px;padding:8px">暂无持仓数据</div>';
    return;
  }
  var list = document.getElementById('holding-list');
  var srcEl = document.getElementById('portfolio-source');
  var timeEl = document.getElementById('portfolio-time');
  if (!list) return;
  var holdings = p.holdings || [];
  if (srcEl) srcEl.textContent = '数据来源: ' + (p.source||'未知');
  if (timeEl && p.lastUpdated) timeEl.textContent = '更新: ' + p.lastUpdated;
  if (!holdings.length) {
    list.innerHTML='<div style="color:var(--text2);font-size:12px;padding:8px">暂无持仓数据</div>';
    var s=document.getElementById('portfolio-summary');
    if(s)s.style.display='none';
    return;
  }
  var totalVal=0, totalCost=0;
  holdings.forEach(function(h){
    totalVal+=(h.price||0)*(h.shares||0);
    totalCost+=(h.cost||0)*(h.shares||0);
  });
  var pnl=totalVal-totalCost;
  var pnlPct=totalCost>0?(pnl/totalCost*100):0;
  var summary=document.getElementById('portfolio-summary');
  if (summary) {
    summary.style.display='';
    var tv=document.getElementById('total-value');
    var tc=document.getElementById('total-cost');
    var pnlEl=document.getElementById('total-pnl');
    if(tv)tv.textContent='¥'+fmtNum(totalVal);
    if(tc)tc.textContent='¥'+fmtNum(totalCost);
    if(pnlEl){
      pnlEl.textContent=(pnl>=0?'+':'')+'¥'+fmtNum(pnl)+' ('+(pnlPct>=0?'+':'')+pnlPct.toFixed(2)+'%)';
      pnlEl.style.color=pnl>=0?'var(--green)':'var(--red)';
    }
  }
  var html = holdings.map(function(h) {
    var val=(h.price||0)*(h.shares||0);
    var cost=(h.cost||0)*(h.shares||0);
    var pnlH=val-cost;
    var pnlPctH=cost>0?(pnlH/cost*100):0;
    return '<div class="task-item"><div class="task-title">'+escHtml(h.name||'')+' <span style="color:var(--text2)">'+escHtml(h.code||'')+'</span></div><div class="task-meta"><span>'+(h.shares||0)+'股</span><span>成本¥'+(h.cost||0)+'</span><span style="color:'+(pnlH>=0?'var(--green)':'var(--red)')+'">'+(pnlH>=0?'+':'')+'¥'+fmtNum(pnlH)+'</span></div><div class="task-detail">'+
      '<div class="task-detail-row"><span class="task-detail-label">现价</span><span>¥'+(h.price||'-')+'</span></div>'+
      '<div class="task-detail-row"><span class="task-detail-label">市值</span><span>¥'+fmtNum(val)+'</span></div>'+
      '<div class="task-detail-row"><span class="task-detail-label">浮亏比例</span><span style="color:'+(pnlPctH>=0?'var(--green)':'var(--red)')+'">'+(pnlPctH>=0?'+':'')+pnlPctH.toFixed(2)+'%</span></div>'+
    '</div></div>';
  }).join('');
  list.innerHTML = html;
}

function renderBackupHealth(b) {
  if (!b) return;
  var scoreEl = document.getElementById('backup-score');
  var statusEl = document.getElementById('backup-status');
  var detailEl = document.getElementById('backup-detail');
  if (scoreEl) scoreEl.textContent = (b.health_score||0)+'分';
  if (statusEl) statusEl.textContent = b.status||'-';
  if (detailEl) detailEl.textContent = b.last_backup||'-';
}

function renderMemoryHealth(m) {
  if (!m) return;
  var scoreEl = document.getElementById('memory-score');
  var statusEl = document.getElementById('memory-status');
  if (scoreEl) scoreEl.textContent = (m.health_score||0)+'分';
  if (statusEl) statusEl.textContent = m.health_status||'-';
}

function renderChangelog(c) {
  var list = document.getElementById('changelog-list');
  var countEl = document.getElementById('changelog-count');
  if (!list) return;
  var changes = Array.isArray(c) ? c : ((c&&c.changes)?c.changes:[]);
  if (countEl) countEl.textContent = changes.length+' 条';
  if (!changes.length) { list.innerHTML='<div style="color:var(--text2);font-size:12px;padding:8px">暂无更新日志</div>'; return; }
  var html = changes.slice(0,5).map(function(i) {
    var dateTag = i.date ? '<span style="font-size:9px;color:var(--text2);margin-left:4px">'+escHtml(i.date)+'</span>' : '';
    var gitTag = i.commit && i.commit!=='-' ? '<span class="task-id">'+i.commit.slice(0,8)+'</span>' : '';
    return '<div class="task-item"><div class="task-title">'+escHtml(i.message||i.title||'')+'</div><div class="task-meta">'+dateTag+gitTag+'</div></div>';
  }).join('');
  list.innerHTML = html;
}

function renderAgentArchitecture(a) {
  var list = document.getElementById('agent-list');
  var countEl = document.getElementById('agent-count');
  if (!list) return;
  var agents = (a && a.agents) || [];
  if (countEl) countEl.textContent = agents.length+' 个Agent';
  if (!agents.length) { list.innerHTML='<div style="color:var(--text2);font-size:12px;padding:8px">暂无Agent数据</div>'; return; }
  var html = agents.map(function(ag) {
    var roleColor = ag.role==='主控'?'var(--blue)':ag.role==='研究'?'var(--purple)':ag.role==='执行'?'var(--green)':ag.role==='验收'?'var(--orange)':'var(--gray)';
    return '<div class="task-item"><div class="task-title">'+escHtml(ag.name||'')+' <span style="color:'+roleColor+';font-size:11px">'+escHtml(ag.role||'')+'</span></div><div class="task-meta"><span style="color:var(--text2);font-size:9px">'+escHtml(ag.last_active||'')+'</span></div><div class="task-detail">'+
      '<div class="task-detail-row"><span class="task-detail-label">状态</span><span>'+escHtml(ag.status||'-')+'</span></div>'+
      '<div class="task-detail-row"><span class="task-detail-label">当前任务</span><span>'+escHtml(ag.current_task||'-')+'</span></div>'+
    '</div></div>';
  }).join('');
  list.innerHTML = html;
}

function renderMultiProject(m) {
  var list = document.getElementById('project-list');
  var countEl = document.getElementById('project-count');
  if (!list) return;
  var projects = (m && m.projects) || [];
  if (countEl) countEl.textContent = projects.length+' 个项目';
  if (!projects.length) { list.innerHTML='<div style="color:var(--text2);font-size:12px;padding:8px">暂无其他项目</div>'; return; }
  var html = projects.map(function(p) {
    return '<div class="task-item"><div class="task-title">'+escHtml(p.name||'')+'</div><div class="task-meta"><span style="font-size:9px">'+escHtml(p.status||'')+'</span></div></div>';
  }).join('');
  list.innerHTML = html;
}

function startCountdown() {
  clearInterval(timer);
  countdown = REFRESH;
  var el = document.getElementById('countdown');
  if (el) el.textContent = countdown;
  timer = setInterval(function() {
    countdown--;
    var el = document.getElementById('countdown');
    if (el) el.textContent = countdown;
    if (countdown <= 0) { clearInterval(timer); fetchAll(); }
  }, 1000);
}

function refreshNow() { clearInterval(timer); fetchAll(); }

document.addEventListener('DOMContentLoaded', fetchAll);
