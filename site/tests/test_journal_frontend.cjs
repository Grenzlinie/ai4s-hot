const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const elements=new Map(),urls=[];
const sandbox={assert,URL,Intl,Date,Set,Map,Number,JSON,console,urls,
 location:{href:'https://example.test/'},history:{pushState:(_,__,u)=>urls.push(String(u))},
 localStorage:{getItem:()=>null},document:{getElementById(id){if(!elements.has(id))elements.set(id,{value:'',checked:false,setAttribute(){}});return elements.get(id);}},setTimeout:()=>0,clearTimeout(){}};
const code=fs.readFileSync(path.join(__dirname,'../static/app.js'),'utf8').replace(/init\(\);\s*$/,'');
vm.runInNewContext(code+`
let checks=0;const eq=(a,b,m)=>{checks++;assert.deepEqual(a,b,m);};
const item=(id,extra={})=>({id,title:id,type:'paper',source_ids:['rss'],content_kind:'web:paper',domain_facets:['web:materials'],first_seen:'2026-10-13T00:00:00Z',...extra});
data={journals:[{id:'nature',title:'Nature',issns:['1476-4687'],publisher:'Springer Nature'},{id:'matter',title:'Matter'},{id:'empty',title:'Zero journal'}],sources:[],taxonomy:{topics:[{id:'materials',name:'Materials',parent_id:null}]},items:[item('a',{journal_id:'nature',journal_relevance:{status:'relevant'},topic_ids:['materials']}),item('b',{journal_id:'matter',journal_relevance:{status:'relevant'},source_ids:['api']}),item('c',{journal_id:'nature',journal_relevance:{status:'pending'}}),item('d')]};
const ids=()=>filtered().map(p=>p.id).sort();reset();eq(ids(),['a','b','d'],'pending hidden by default');
selectedJournals=new Set(['nature','matter']);eq(ids(),['a','b'],'journals OR');
selectedSources=new Set(['rss']);eq(ids(),['a'],'source AND journal');selectedSources.clear();
selectedTopics=new Set(['materials']);eq(ids(),['a'],'topic AND journal');selectedTopics.clear();
kind='web:model_release';eq(ids(),[],'kind AND journal');kind='';domain='web:life_sciences';eq(ids(),[],'domain AND journal');domain='';
viewMode='latest';eq(ids(),['a','b'],'latest preserves journals');saved=new Set(['a','b','c']);savedView=true;eq(ids(),['a','b'],'saved preserves journals and review');
journalReview='pending';eq(ids(),['c'],'pending mode only shows pending journal articles');selectedJournals=new Set(['matter']);eq(ids(),[],'pending mode still respects journal');
reset();savedView=false;selectedJournals=new Set(['empty']);eq(ids(),[],'zero-result journal valid');renderJournals();eq($('all-journals').innerHTML.includes('Zero journal'),true,'zero-result journal remains selectable');
reset();selectedJournals=new Set(['nature']);journalReview='pending';syncURL();location.href=urls.at(-1);reset();restoreURL();eq([...selectedJournals],['nature'],'journal URL restore');eq(journalReview,'pending','review URL restore');
clearFilter('journal:nature');eq(selectedJournals.size,0,'single clear');clearFilter('journal-review');eq(journalReview,'','review clear');
location.href='https://example.test/?journals=unknown,nature&journal_review=evil';restoreURL();eq([...selectedJournals],['nature'],'unknown journal ignored');eq(journalReview,'','unknown review ignored');
reset();$('query').value='nature';data.items[0].journal_title='Nature';eq(ids(),['a'],'journal name searchable');
data.items[0].journal_title='<img src=x onerror=alert(1)>';eq(card(data.items[0]).includes('<img src=x'),false,'journal title escaped');
delete data.journals;location.href='https://example.test/?journals=nature&journal_review=pending';reset();restoreURL();eq(selectedJournals.size,0,'legacy archive journal compatibility');eq(journalReview,'','legacy archive review compatibility');
eq(journalReason('abstract_missing_or_insufficient'),'摘要缺失或信息不足，尚无法确认材料 AI 相关性','readable reason code');eq(healthLabels.partial,'部分采集成功','readable partial health');eq(journalHealth({kind:'journal',counters:{fetched:20,relevant:2,pending:3,excluded:15},errors:['crossref_page_cap_reached']}).includes('窗口内相关 2 · 待确认 3 · 排除 15'),true,'journal counters visible');eq(journalHealth({kind:'journal',errors:['rss_request_or_parse_failed']}).includes('期刊订阅源暂时无法读取'),true,'readable journal error');
console.log('Journal frontend: '+checks+' behavioral assertions passed');
`,sandbox);
