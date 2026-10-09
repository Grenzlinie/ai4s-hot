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

// Retired topics remain browseable history, while corrections require active targets.
data.taxonomy.topics.push({id:'retiredleaf',parent_id:'materials',name:'Archived material',path:'materials / Archived material',active:false,retired:true});
data.taxonomy.aliases.oldretired='retiredleaf';
data.items.push({...data.items[0],id:'history',topic_labels:undefined,topic_leaf_ids:['retiredleaf']});
data.items.push({...data.items[0],id:'overridehistory',topic_labels:[{label_id:'ml'}],topic_override:{topic_ids:['retiredleaf'],status:'needs_review'}});
corrections={a:{topic_ids:['retiredleaf'],reason:'Historical correction'}};
assert.equal(taxonomyTopics().some(t=>t.id==='retiredleaf'),true);
assert.equal(activeTopics().some(t=>t.id==='retiredleaf'),false);
assert.equal(localCorrectionUsable(data.items[0]),false);
assert.deepEqual(leafIDs(data.items[0]),['mof','ml']);
assert.match(classificationEvidence(data.items[0]),/需要复核/);
assert.equal(leafIDs(data.items.at(-1)).includes('retiredleaf'),false);
assert.equal(browseIDs(data.items.at(-1)).has('retiredleaf'),true);
assert.match(classificationEvidence(data.items.at(-1)),/全站人工修正待复核/);
$('query').value='';$('source').value='';$('unread').checked=false;selectedTopics=new Set(['retiredleaf']);days=0;
assert.deepEqual(filtered().map(p=>p.id),['history','overridehistory']);
assert.deepEqual(topicCounts('retiredleaf'),[2,2]);
$('topic-search').value='';expandedTopics.add('materials');assert.match(topicNavigation(),/retired-badge/);assert.match(topicName('retiredleaf'),/已归档/);
location.href='https://example.test/?days=0&topics=oldretired';restoreURL();assert.equal(selectedTopics.has('retiredleaf'),true);assert.equal(filtered().length,2);
location.href='https://example.test/?days=0&topics=zotero:unknown&q=keep';restoreURL();assert.equal(selectedTopics.size,0);assert.equal($('query').value,'keep');assert.match($('toast').textContent,/当前归档不支持部分主题筛选/);
corrections.a={topic_ids:[],reason:'Explicitly no research topic'};assert.equal(itemIDs(data.items[0]).size,0);

corrections={};data.items.push({...data.items[0],id:'historyfield',topic_labels:[],topic_ids:[],topic_leaf_ids:[],topic_history:[{id:'retiredleaf'}]});
assert.equal(leafIDs(data.items.at(-1)).includes('retiredleaf'),true);assert.equal(browseIDs(data.items.at(-1)).has('retiredleaf'),true);assert.match(classificationEvidence(data.items.at(-1)),/已归档的历史分类/);
const receipt={schema_version:1,status:'error',stage:'classification',last_attempt:'2026-10-09T00:00:00Z',last_success:'2026-10-08T00:00:00Z',retryable:true,failed_item_id:'a'};
assert.equal(validateUpdateStatus(receipt),receipt);assert.equal(validateUpdateStatus({...receipt,stage:'unknown'}),null);assert.equal(validateUpdateStatus({...receipt,private_token:'not-allowed'}),null);assert.equal(validateUpdateStatus({...receipt,last_attempt:'bad'}),null);
updateStatus=receipt;assert.match(updateHealth(),/本次更新失败/);assert.match(updateHealth(),/保留上次结果/);assert.match(classificationEvidence(data.items[0]),/本次分类更新失败/);assert.doesNotMatch(classificationEvidence(data.items[1]),/本次分类更新失败/);updateStatus=null;data.generated_at='2000-01-01T00:00:00Z';assert.match(updateHealth(),/超过 36 小时/);
`,sandbox);
console.log('Topic explorer: 67 assertions passed (pure behavior; not browser acceptance)');
