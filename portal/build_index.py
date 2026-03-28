#!/usr/bin/env python3
"""
build_index.py - 生成门户页 index.html
读取 system.json / portfolio.json / tasks.json 动态生成
"""
import json, subprocess, os
from datetime import datetime

WORKSPACE = "/home/admin/openclaw/workspace"
STATUS_DIR = f"{WORKSPACE}/portal/status"

def get_git_log(limit=8):
    try:
        result = subprocess.run(
            ["git", "log", f"--oneline", f"-{limit}", "--since=24 hours ago"],
            capture_output=True, text=True, cwd=WORKSPACE
        )
        return [l.strip() for l in result.stdout.strip().split('\n') if l.strip()]
    except:
        return []

def get_system_data():
    try:
        with open(f"{STATUS_DIR}/system.json") as f:
            return json.load(f)
    except:
        return {}

def get_portfolio():
    try:
        with open(f"{STATUS_DIR}/portfolio.json") as f:
            return json.load(f)
    except:
        return {}

def get_tasks():
    try:
        with open(f"{STATUS_DIR}/tasks.json") as f:
            return json.load(f)
    except:
        return {}

# 生成 JS fetch 代码
js_fetch = """
fetch('./status/system.json').then(r=>r.json()).then(function(d){
  var agents=[{zh:'主控 Agent',s:'活跃'},{zh:'研究 Agent',s:'就绪'},{zh:'执行 Agent',s:'就绪'},{zh:'验收 Agent',s:'就绪'},{zh:'学习复盘',s:'就绪'}];
  if(d.openclaw&&d.openclaw.gitCommit){
    document.getElementById('git-commit').textContent='Git: '+d.openclaw.gitCommit;
  }
  if(d.lastUpdated){
    var ud=new Date(d.lastUpdated);
    document.getElementById('last-update').textContent=ud.toLocaleString('zh-CN',{timeZone:'Asia/Shanghai'});
  }
}).catch(function(e){console.log(e)});

fetch('./status/portfolio.json').then(r=>r.json()).then(function(d){
  var hs=d.holdings||[];
  var sum=d.summary||{};
  var tag=document.getElementById('portfolio-tag');
  var scan=document.getElementById('scan-result');
  var sumDiv=document.getElementById('portfolio-summary');
  if(hs.length>0){
    tag.textContent='持仓 '+hs.length+' 只';tag.className='tag success';
    var tp=sum.total_profit||0,tpp=sum.total_profit_pct||0;
    var tprofit=sum.today_profit_pct||0;
    var tsign=tp>=0?'+':'',psign=tpp>=0?'+':'';
    sumDiv.innerHTML='<div class="summary-row"><span class="summary-label">总盈亏</span><span class="summary-value '+(tp>=0?'neutral':'loss')+'">'+tsign+'¥'+tp+' ('+psign+tpp+'%)</span></div><div class="summary-row"><span class="summary-label">今日盈亏</span><span class="summary-value '+(tprofit>=0?'neutral':'loss')+'">'+psign+tprofit.toFixed(2)+'%</span></div>';
    scan.style.display='block';
    var h='';
    hs.forEach(function(st){
      var pf=st.profit_pct||0,ch=st.change_pct||0;
      var sP=pf>=0?'+':'',sC=ch>=0?'+':'';
      h+='<div class="stock-card"><div class="stock-card-name">'+st.name+' ('+st.code+')</div><div class="stock-card-prices"><div class="scp"><span class="scp-label">现价</span><span class="scp-val">¥'+st.price+'</span></div><div class="scp"><span class="scp-label">今日</span><span class="scp-val '+(ch>=0?'gain':'loss')+'">'+sC+ch.toFixed(2)+'%</span></div><div class="scp"><span class="scp-label">浮盈亏</span><span class="scp-val '+(pf>=0?'gain':'loss')+'">'+sP+pf.toFixed(2)+'%</span></div><div class="scp"><span class="scp-label">成本</span><span class="scp-val">¥'+st.cost+'</span></div></div></div>';
    });
    scan.innerHTML=h;
  } else {
    tag.textContent='暂无持仓';tag.className='tag';
    sumDiv.innerHTML='<div style="color:#64748b">暂无数据</div>';
    scan.style.display='none';
  }
}).catch(function(e){console.log(e)});

fetch('./status/tasks.json').then(r=>r.json()).then(function(d){
  var pools=[{k:'doing',l:'🔄 进行中'},{k:'todo',l:'⏳ 待办'},{k:'done',l:'✅ 已完成'}];
  var html='<div class="task-section">';
  pools.forEach(function(p){
    var pool=d[p.k]||[];
    if(pool.length>0){
      html+='<div class="task-pool-label">'+p.l+' ('+pool.length+')</div>';
      pool.forEach(function(t){
        var tid=t.id||p.k+'_'+(Math.random().toString(36).substr(2,5));
        html+='<div class="task-item"><div class="task-header"><span class="task-name">'+t.name+'</span></div>';
        html+='<div class="task-meta">'+t.date+'</div>';
        if(t.result&&t.result!=='无')html+='<div class="task-meta" style="color:#86efac">'+t.result.substring(0,60)+'</div>';
        html+='</div>';
      });
    }
  });
  html+='</div>';
  document.getElementById('task-list').innerHTML=html||'<div style="color:#64748b">暂无任务</div>';
}).catch(function(e){console.log(e)});
"""

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OpenClaw 个人 AI 指挥中心</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh}}
.container{{max-width:1100px;margin:0 auto;padding:1.5rem}}
header{{text-align:center;margin-bottom:2rem;padding-top:1rem}}
h1{{font-size:2rem;margin-bottom:0.3rem;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.subtitle{{color:#94a3b8;font-size:0.95rem}}
.status-bar{{display:flex;gap:0.8rem;justify-content:center;margin-bottom:1.5rem;flex-wrap:wrap;font-size:0.85rem;color:#94a3b8}}
.tag{{background:#334155;padding:0.2rem 0.7rem;border-radius:999px;font-size:0.8rem}}
.tag.success{{background:#166534;color:#86efac}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1rem}}
.card{{background:#1e293b;border-radius:0.75rem;padding:1rem;border:1px solid #334155}}
.card h3{{font-size:0.85rem;color:#667eea;margin-bottom:0.6rem;display:flex;align-items:center;gap:0.4rem}}
.section h3{{font-size:0.9rem;color:#667eea;margin-bottom:0.5rem}}
.summary-row{{display:flex;justify-content:space-between;padding:0.35rem 0;border-bottom:1px solid #334155}}
.summary-row:last-child{{border-bottom:none}}
.summary-label{{color:#94a3b8;font-size:0.88rem}}
.summary-value{{font-size:0.95rem;font-weight:600}}
.gain{{color:#86efac}}
.loss{{color:#f87171}}
.neutral{{color:#e2e8f0}}
.stock-card{{background:#0f172a;border-radius:0.5rem;padding:0.7rem;margin-top:0.5rem;border:1px solid #334155}}
.stock-card-name{{font-size:0.9rem;color:#f8fafc;margin-bottom:0.3rem;font-weight:600}}
.stock-card-prices{{display:flex;gap:0.8rem;flex-wrap:wrap}}
.scp{{display:flex;flex-direction:column}}
.scp-label{{font-size:0.68rem;color:#64748b}}
.scp-val{{font-size:0.85rem}}
.task-pool-label{{font-size:0.82rem;color:#94a3b8;margin:0.5rem 0 0.3rem;border-bottom:1px solid #1e293b;padding-bottom:0.2rem}}
.task-item{{padding:0.5rem;background:#0f172a;border-radius:0.4rem;margin-bottom:0.3rem;border:1px solid #1e293b;cursor:default}}
.task-header{{display:flex;justify-content:space-between;align-items:center}}
.task-name{{font-size:0.88rem;color:#e2e8f0}}
.task-meta{{font-size:0.75rem;color:#64748b;margin-top:0.15rem}}
.task-list-note{{font-size:0.75rem;color:#475569;margin-bottom:0.3rem}}
.commit-item{{font-size:0.8rem;color:#94a3b8;padding:0.2rem 0;border-bottom:1px solid #1e293b}}
.commit-item:last-child{{border-bottom:none}}
.full-width{{grid-column:1/-1}}
@media(max-width:700px){{.grid{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<div class="container">
<header>
<h1>OpenClaw 个人 AI 指挥中心</h1>
<p class="subtitle">多 Agent 协同 · A股辅助 · 实时监控</p>
</header>
<div class="status-bar">
<span id="last-update">加载中...</span>
<span id="git-commit">-</span>
</div>
<div class="grid">
<div class="card">
<h3>📊 系统状态</h3>
<div class="summary-row"><span class="summary-label">Gateway</span><span class="summary-value gain">运行中</span></div>
<div class="summary-row"><span class="summary-label">主 Agent</span><span class="summary-value">活跃</span></div>
<div class="summary-row"><span class="summary-label">MCP 数据源</span><span class="summary-value gain">正常</span></div>
<div class="summary-row"><span class="summary-label">Feishu</span><span class="summary-value gain">已配置</span></div>
<div class="summary-row"><span class="summary-label">止损监控</span><span class="summary-value gain">已注册</span></div>
</div>
<div class="card">
<h3 id="portfolio-tag" class="tag">暂无持仓</h3>
<div id="portfolio-summary" style="margin-top:0.5rem">
<div style="color:#64748b">暂无数据</div>
</div>
<div id="scan-result" style="display:none;margin-top:0.5rem"></div>
</div>
<div class="card">
<h3>📈 持仓</h3>
<div id="portfolio-summary2"><div style="color:#64748b">加载中...</div></div>
</div>
<div class="card">
<h3>🤖 Agent 协作</h3>
<div class="summary-row"><span class="summary-label">研究 Agent</span><span class="summary-value gain">待命</span></div>
<div class="summary-row"><span class="summary-label">执行 Agent</span><span class="summary-value gain">待命</span></div>
<div class="summary-row"><span class="summary-label">验收 Agent</span><span class="summary-value gain">待命</span></div>
<div class="summary-row"><span class="summary-label">学习复盘</span><span class="summary-value gain">待命</span></div>
</div>
</div>
<div class="card full-width">
<h3>📋 任务池</h3>
<div id="task-list"><div style="color:#64748b">加载中...</div></div>
</div>
<div class="card full-width">
<h3>📝 最近工作（24小时内）</h3>
<div id="commit-list"><div style="color:#64748b">加载中...</div></div>
</div>
</div>
<script>
(js_fetch_code)
document.addEventListener('DOMContentLoaded',function(){{
  // 加载最近 commit
  fetch('./status/system.json').then(r=>r.json()).then(function(d){{
    var cl=document.getElementById('commit-list');
    if(d.openclaw&&d.openclaw.gitCommit){{
      cl.innerHTML='<div class="commit-item">最新: '+d.openclaw.gitCommit+'</div>';
    }}
  }}).catch(function(){{}});
}});
</script>
</body>
</html>"""

# 注入 JS
html = html.replace("(js_fetch_code)", js_fetch)

with open('index.html', 'w') as f:
    f.write(html)

# 同时更新 system.json 的 git commit
system = get_system_data()
result = subprocess.run(["git","rev-parse","--short","HEAD"], capture_output=True, text=True, cwd=WORKSPACE)
commit = result.stdout.strip()
result2 = subprocess.run(["git","rev-list","--count","HEAD"], capture_output=True, text=True, cwd=WORKSPACE)
total = result2.stdout.strip()
system.setdefault('openclaw', {})['gitCommit'] = commit
system.setdefault('openclaw', {})['totalCommits'] = int(total) if total.isdigit() else 0
system['lastUpdated'] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f+08:00')
with open(f'{STATUS_DIR}/system.json', 'w') as f:
    json.dump(system, f, indent=2, ensure_ascii=False)

print(f"Generated index.html ({len(html)} bytes)")
print(f"Updated system.json: commit={commit} total={total}")
