'use strict';
const $ = id => document.getElementById(id);
const labels = {all:'全部进展',science:'AI for Science',materials:'材料与能源',chemistry:'化学与分子',biology:'生命科学',agents:'科研智能体',tools:'代码与工具',frontier:'前沿模型',papers:'论文'};
const symbols = {all:'◎',materials:'◇',chemistry:'⌬',biology:'✧',agents:'⊞',tools:'⌘',frontier:'△'};
const types = {paper:'论文',report:'技术报告 / 官方文章',code:'官方仓库更新',release:'模型 / 代码发布'};
const summaryLabels = {ai_summary:'AI 中文摘要',upstream_tldr:'Zotero 推荐摘要',source_excerpt:'来源摘录'};
const healthLabels = {ok:'采集成功',error:'采集失败',needs_config:'待配置',pending:'等待论文归档'};
let data, topic='', channel='', days=30, savedView=false, shown=25;
let read = readStorage('ai4s-read'), saved = readStorage('ai4s-saved');
let storageWarning = false;
function readStorage(key){try{return new Set(JSON.parse(localStorage.getItem(key)||'[]'));}catch{return new Set();}}
function persist(){try{localStorage.setItem('ai4s-read',JSON.stringify([...read]));localStorage.setItem('ai4s-saved',JSON.stringify([...saved]));}catch{if(!storageWarning){toast('浏览器未允许保存，当前标记仅在本次页面中有效');storageWarning=true;}}$('saved-count').textContent=saved.size;}
function escapeText(value){return String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function safeURL(value){try{const u=new URL(value);return ['https:','http:'].includes(u.protocol)?u.href:'#';}catch{return '#';}}
function date(value, full=false){if(!value)return '日期未提供';const d=new Date(value);if(Number.isNaN(d.getTime()))return '日期未提供';return new Intl.DateTimeFormat('zh-CN',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit',...(full?{hour:'2-digit',minute:'2-digit'}:{})}).format(d);}
function localDay(value){const d=new Date(value);if(Number.isNaN(d.getTime()))return '';return new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit'}).format(d);}
let toastTimer;
function toast(message){$('toast').textContent=message;$('toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').hidden=true,3000);}
function filtered(){const query=$('query').value.trim().toLocaleLowerCase();const source=$('source').value;const archiveDate=$('archive-date').value;const cutoff=Date.now()-days*86400000;const sort=$('sort').value;
  const results=data.items.filter(p=>{
    if(savedView&&!saved.has(p.id))return false;
    if(topic==='unclassified'&&(p.topic_ids||[]).length)return false;
    if(topic&&topic!=='unclassified'&&!(data.taxonomy?.topics?.length?p.topic_ids||[]:p.tags).includes(topic))return false;
    if(channel&&!(p.groups||[p.group]).includes(channel)&&!(channel==='papers'&&p.type==='paper'))return false;
    if(source&&!p.source_ids.includes(source))return false;
    if($('unread').checked&&read.has(p.id))return false;
    if(archiveDate){if(localDay(p.first_seen)!==archiveDate)return false;}
    else if(days&&new Date(p.published_at||p.first_seen).getTime()<cutoff)return false;
    if(sort==='zotero'&&(!p.source_ids.includes('zotero')||!Number.isFinite(p.zotero_score)))return false;
    if(sort==='alpha'&&!Number.isFinite(p.alpha_rank))return false;
    return !query||[p.title,p.summary,p.excerpt,...p.source_names,...(p.authors||[])].join(' ').toLocaleLowerCase().includes(query);
  });
  results.sort((a,b)=>sort==='zotero'?b.zotero_score-a.zotero_score:sort==='alpha'?a.alpha_rank-b.alpha_rank:new Date(sort==='indexed'?b.first_seen:(b.published_at||b.first_seen))-new Date(sort==='indexed'?a.first_seen:(a.published_at||a.first_seen)));
  return results;
}
function card(p){const isRead=read.has(p.id),isSaved=saved.has(p.id);const summary=p.summary||p.excerpt||'来源未提供摘要，点击标题查看原文。';const shortened=summary.length>420?summary.slice(0,420)+'…':summary;const signals=[];if(Number.isFinite(p.zotero_score))signals.push('Zotero 相似度 '+p.zotero_score.toFixed(3));if(Number.isFinite(p.alpha_rank))signals.push('alphaXiv 近 30 天榜单 #'+p.alpha_rank);
  return `<article class="entry ${isRead?'is-read':''}" id="item-${escapeText(p.id)}"><div class="entry-meta"><span class="type-label type-${escapeText(p.type)}">${escapeText(types[p.type]||'进展')}</span><span>${escapeText(p.source_names.join(' / '))}</span><time datetime="${escapeText(p.published_at||p.first_seen)}">${p.published_at?'发表':'收录'} ${escapeText(date(p.published_at||p.first_seen))}</time></div><h3><a href="${escapeText(safeURL(p.url))}" target="_blank" rel="noopener noreferrer" data-open="${escapeText(p.id)}">${escapeText(p.title)}</a></h3><p class="summary">${escapeText(shortened)}</p><p class="summary-kind">${escapeText(summaryLabels[p.summary_kind]||'来源摘录')}</p>${signals.length?`<p class="signals">${escapeText(signals.join('；'))}</p>`:''}<div class="entry-bottom"><div class="tags">${itemTopics(p)}</div><div class="actions"><button data-read="${escapeText(p.id)}" class="${isRead?'selected':''}" aria-pressed="${isRead}">${isRead?'已读':'标为已读'}</button><button data-save="${escapeText(p.id)}" class="${isSaved?'selected':''}" aria-pressed="${isSaved}">${isSaved?'★ 已收藏':'☆ 收藏'}</button><button data-share="${escapeText(p.id)}">链接</button></div></div><details><summary>查看摘要与记录</summary>${p.authors?.length?`<p>作者：${escapeText(p.authors.join(', '))}</p>`:''}<p>${escapeText(summary)}</p><p>首次收录：${escapeText(date(p.first_seen,true))}${p.published_at?'；来源发表日期：'+escapeText(date(p.published_at)):''}</p>${p.pdf_url?`<a href="${escapeText(safeURL(p.pdf_url))}" target="_blank" rel="noopener noreferrer">论文 PDF</a>`:''}</details></article>`;
}
function topicName(id){return id==='unclassified'?'待分类':data.taxonomy?.topics?.find(t=>t.id===id)?.path||labels[id]||id;}
function itemTopics(p){const ids=data.taxonomy?.topics?.length?(p.topic_leaf_ids||[]):p.tags;return ids.length?ids.map(t=>`<button class="tag" data-topic="${escapeText(t)}">${escapeText(topicName(t))}</button>`).join(''):'<span class="tag">主题待分类</span>';}
function topicNavigation(){
  const topics=data.taxonomy?.topics||[];
  if(!topics.length)return ['all','materials','chemistry','biology','agents','tools','frontier'].map(t=>`<button data-topic="${t==='all'?'':t}"><i class="topic-symbol" aria-hidden="true">${symbols[t]}</i>${labels[t]}<span>${t==='all'?data.items.length:data.items.filter(p=>p.tags.includes(t)).length}</span></button>`).join('');
  function branch(t){const children=topics.filter(c=>c.parent_id===t.id);const count=data.items.filter(p=>(p.topic_ids||[]).includes(t.id)).length;const button=`<button data-topic="${escapeText(t.id)}" title="${escapeText(t.path)}">${escapeText(t.name)}<span>${count}</span></button>`;return children.length?`<details class="topic-branch"><summary>${button}</summary><div class="topic-children">${children.map(branch).join('')}</div></details>`:button;}
  return `<button data-topic="">全部进展<span>${data.items.length}</span></button>`+topics.filter(t=>!t.parent_id).map(branch).join('')+`<button data-topic="unclassified">待分类<span>${data.items.filter(p=>!(p.topic_ids||[]).length).length}</span></button>`;
}
function render(){const results=filtered();$('result-count').textContent=results.length+' 条';$('results-title').textContent=savedView?'我的收藏':topic?topicName(topic):channel?labels[channel]:'进展时间线';$('entries').innerHTML=results.length?results.slice(0,shown).map(card).join(''):`<div class="empty"><b>${savedView?'还没有符合筛选条件的收藏':'这个范围里暂时没有内容'}</b>${savedView?'点击条目下方的「收藏」，稍后继续阅读。':'试试全部归档、其他来源，或清空关键词。'}</div>`;$('load-more').hidden=shown>=results.length;document.querySelectorAll('[data-topic]').forEach(b=>b.classList.toggle('active',(b.dataset.topic||'')===topic));document.querySelectorAll('[data-channel]').forEach(b=>b.classList.toggle('active',(b.dataset.channel||'')===channel));$('saved').classList.toggle('active',savedView);$('home').classList.toggle('active',!savedView);$('saved-count').textContent=saved.size;}
function refresh(){shown=25;render();}
function reset(){topic='';channel='';days=30;$('source').value='';$('query').value='';$('archive-date').value='';$('sort').value='recent';$('unread').checked=false;document.querySelectorAll('[data-days]').forEach(b=>b.classList.toggle('active',Number(b.dataset.days)===days));}
function health(){const okay=data.sources.filter(s=>s.status==='ok').length;$('coverage').textContent=`${data.items.length} 条归档，${okay}/${data.sources.length} 个来源本次采集成功`;
  $('health').innerHTML=`<p>来源失败时保留已归档内容。初次采集回看 ${escapeText(data.policy.lookback_days)} 天，每个来源每次最多收录 ${escapeText(data.policy.max_items_per_source)} 条；alphaXiv 为近 30 天热门榜。主题目录：${escapeText(({ok:'已同步',stale:'使用上次目录',error:'同步失败',unconfigured:'待配置'})[data.taxonomy?.status]||'待同步')}，标签依据库内文献相似度自动推断。摘要：${escapeText(data.summaries.status)}，本次生成 ${escapeText(data.summaries.generated)} 条。</p><div class="health-list">${data.sources.map(s=>`<div class="health-item"><div><a href="${escapeText(safeURL(s.url))}" target="_blank" rel="noopener noreferrer">${escapeText(s.name)}</a><small>最近成功：${escapeText(date(s.last_success,true))}${s.message?'<br>'+escapeText(s.message):''}</small></div><span class="status-${escapeText(s.status)}">${escapeText(healthLabels[s.status]||s.status)}${s.status==='ok'?' · '+escapeText(s.count):''}</span></div>`).join('')}</div>`;
}
async function init(){try{const response=await fetch('./data/index.json',{cache:'no-cache'});if(!response.ok)throw Error('archive unavailable');data=await response.json();if(data.schema_version!==1||!Array.isArray(data.items))throw Error('invalid archive');
  $('updated').textContent='归档更新于 '+date(data.generated_at,true);$('archive-date').max=localDay(data.generated_at);
  $('topic-heading').textContent=data.taxonomy?.topics?.length?'Zotero 主题目录':'阅读方向';
  $('topics').innerHTML=topicNavigation();
  $('topics').classList.toggle('zotero-topics',Boolean(data.taxonomy?.topics?.length));
  $('channels').innerHTML=['all','science','frontier','tools','papers'].map(t=>`<button data-channel="${t==='all'?'':t}" class="${t==='all'?'active':''}">${t==='all'?'全部':labels[t]}</button>`).join('');
  data.sources.forEach(s=>{const option=document.createElement('option');option.value=s.id;option.textContent=s.name;$('source').append(option);});health();persist();
  document.addEventListener('click',async event=>{const b=event.target.closest('button,a');if(!b)return;if(b.dataset.topic!==undefined){event.preventDefault();topic=b.dataset.topic;refresh();}if(b.dataset.channel!==undefined){channel=b.dataset.channel;refresh();}if(b.dataset.days!==undefined){days=Number(b.dataset.days);$('archive-date').value='';document.querySelectorAll('[data-days]').forEach(el=>el.classList.toggle('active',el===b));refresh();}if(b.dataset.read){read.has(b.dataset.read)?read.delete(b.dataset.read):read.add(b.dataset.read);persist();render();}if(b.dataset.open){read.add(b.dataset.open);persist();}if(b.dataset.save){saved.has(b.dataset.save)?saved.delete(b.dataset.save):saved.add(b.dataset.save);persist();render();}if(b.dataset.share){const url=new URL(location.href);url.search='';url.hash='item-'+b.dataset.share;try{await navigator.clipboard.writeText(url.href);toast('条目链接已复制');}catch{toast('复制受限，可从地址栏复制当前链接');location.hash=url.hash;}}});
  $('query').addEventListener('input',refresh);['source','sort','unread','archive-date'].forEach(id=>$(id).addEventListener('change',refresh));$('clear').onclick=()=>{reset();refresh();};$('load-more').onclick=()=>{shown+=25;render();};$('saved').onclick=()=>{savedView=true;reset();days=0;document.querySelectorAll('[data-days]').forEach(b=>b.classList.toggle('active',Number(b.dataset.days)===0));refresh();};$('home').onclick=()=>{savedView=false;reset();refresh();};$('health-toggle').onclick=()=>{const open=$('health').hidden;$('health').hidden=!open;$('health-toggle').setAttribute('aria-expanded',String(open));};
  $('export-saved').onclick=()=>{const content={exported_at:new Date().toISOString(),items:data.items.filter(p=>saved.has(p.id))};const blob=new Blob([JSON.stringify(content,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='ai4s-hot-collections.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
  document.addEventListener('keydown',e=>{if(e.key==='/'&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)){e.preventDefault();$('query').focus();}});
  if(location.hash.startsWith('#item-')){days=0;const id=location.hash.slice(6);const index=filtered().findIndex(p=>p.id===id);shown=Math.max(25,index+1);document.querySelectorAll('[data-days]').forEach(b=>b.classList.toggle('active',Number(b.dataset.days)===0));}render();if(location.hash)document.getElementById(location.hash.slice(1))?.scrollIntoView();
}catch{$('updated').textContent='归档暂时无法读取';$('coverage').textContent='请刷新页面，或查看 GitHub Actions 的最近运行';$('entries').innerHTML='<div class="empty"><b>归档暂时不可用</b>请稍后刷新页面。<br><a href="https://github.com/Grenzlinie/ai4s-hot/actions">查看更新任务</a></div>';}}
init();
