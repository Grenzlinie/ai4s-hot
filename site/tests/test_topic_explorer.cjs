// Pure behavior tests; real browser/accessibility checks remain a separate gate.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const els=new Map(),storage=new Map(),historyURLs=[];
const sandbox={historyURLs,assert,URL,Intl,Date,Set,Map,Number,JSON,console,location:{href:'https://example.test/ai4s-hot/'},history:{pushState:(_,__,u)=>historyURLs.push(String(u)),replaceState:(_,__,u)=>historyURLs.push(String(u))},localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)},document:{getElementById(id){if(!els.has(id))els.set(id,{value:'',checked:false,textContent:'',hidden:true});return els.get(id);}},setTimeout:()=>0,clearTimeout:()=>{}};
const src=fs.readFileSync(require('node:path').join(__dirname,'../static/app.js'),'utf8').replace(/init\(\);\s*$/,'');
vm.runInNewContext(src+`
const t=(id,parent_id=null)=>({id,parent_id,name:id,path:id});
data={taxonomy:{topics:[t('materials'),t('mof','materials'),t('metal','materials'),t('methods'),t('ml','methods'),t('bo','methods')],aliases:{oldmof:'mof'}},items:[
 {id:'a',title:'MOF machine learning',topic_labels:[{label_id:'mof'},{label_id:'ml'}],source_ids:['hf'],source_names:['HF'],first_seen:'2026-10-09',type:'paper'},
 {id:'b',title:'Metal Bayesian',topic_leaf_ids:['metal','bo'],source_ids:['zotero'],source_names:['Zotero'],first_seen:'2026-10-09',type:'paper'},
 {id:'c',title:'MOF Bayesian',topic_leaf_ids:['mof','bo'],source_ids:['hf'],source_names:['HF'],first_seen:'2026-10-09',type:'paper'},
 {id:'d',title:'Company announcement',topic_leaf_ids:[],source_ids:['official'],source_names:['Official'],first_seen:'2026-10-09',type:'report'}]};days=0;
selectedTopics=new Set(['ml','bo','mof']);
assert.deepEqual(filtered().map(p=>p.id),['a','c'],'same axis OR; across axes AND');
assert.deepEqual(topicCounts('bo'),[1,2],'own-axis selection ignored; material selection retained');
assert.deepEqual(topicCounts('metal'),[1,1],'material counts ignore current material selection');
$('source').value='hf';assert.deepEqual(topicCounts('metal'),[0,1],'source filter retained in counts');
$('source').value='';$('query').value='Bayesian';assert.deepEqual(filtered().map(p=>p.id),['c']);
$('query').value='';selectedTopics=new Set(['materials']);assert.equal(filtered().length,3,'parent includes descendants');
data.items.push(data.items[0]);assert.equal(filtered().length,3,'duplicate IDs counted once');assert.deepEqual(topicCounts('materials'),[3,3]);data.items.pop();
selectedTopics=new Set(['unclassified']);assert.deepEqual(filtered().map(p=>p.id),['d']);
selectedTopics.clear();corrections.a={topic_ids:['metal'],reason:'公开摘要为金属材料',created_at:'2026-10-09T00:00:00Z'};assert.deepEqual(leafIDs(data.items[0]),['metal']);assert.equal(itemIDs(data.items[0]).has('materials'),true);
const exported=correctionExport();assert.deepEqual(Object.keys(exported).sort(),['overrides','schema_version']);assert.deepEqual(Object.keys(exported.overrides[0]).sort(),['author','created_at','item_id','reason','topic_ids','version']);assert.equal(exported.overrides[0].version,1);
corrections.a.topic_ids=['retired'];assert.deepEqual(leafIDs(data.items[0]),['mof','ml'],'retired local correction falls back and is visibly marked');assert.match(classificationEvidence(data.items[0]),/需要复核/);
corrections={};location.href='https://example.test/ai4s-hot/?topics=oldmof,bo&q=MOF&days=0&source=hf&sort=indexed&view=saved&unread=1';restoreURL();assert.deepEqual([...selectedTopics],['mof','bo']);assert.equal(savedView,true);assert.equal($('query').value,'MOF');assert.equal(days,0);assert.equal($('unread').checked,true);assert.equal(expandedTopics.has('materials'),true);assert.equal($('sort').value,'indexed');syncURL();assert.match(historyURLs.at(-1),/topics=bo%2Cmof/);assert.match(historyURLs.at(-1),/view=saved/);
clearFilter('topic:mof');assert.equal(selectedTopics.has('mof'),false);clearFilter('query');assert.equal($('query').value,'');clearFilter('saved');assert.equal(savedView,false);
$('topic-search').value='mof';const nav=topicNavigation();assert.match(nav,/data-topic="materials"/);assert.match(nav,/data-topic="mof"/);assert.doesNotMatch(nav,/data-topic="metal"/);assert.match(nav,/aria-expanded="true"/);
assert.equal(classificationEvidence({topic_status:'insufficient_evidence'}).includes('公开信息不足'),true);
assert.equal(classificationEvidence({topic_status:'broad_only',topic_labels:[{label_id:'mof',score:.75,public_reason:'<script>no</script>'}]}).includes('<script>'),false);
assert.match(classificationEvidence({id:'v1-pending',topic_ids:[],topic_leaf_ids:[]}),/等待分类/);
assert.doesNotMatch(classificationEvidence({id:'v1-pending',topic_ids:[],topic_leaf_ids:[]}),/已推断细分类/);
assert.match(classificationEvidence({id:'v1-classified',topic_ids:['mof'],topic_leaf_ids:['mof']}),/已推断细分类/);
`,sandbox);
console.log('Topic explorer: 37 assertions passed (pure behavior; not browser acceptance)');
