// Exercise pure UI behavior in a minimal DOM, without a browser or network.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const elements = new Map();
const sandbox = {
  assert, URL, Intl, Date, Set, Number,
  localStorage: {getItem: () => null, setItem: () => {}},
  document: {getElementById(id) {
    if (!elements.has(id)) elements.set(id, {value:'', checked:false});
    return elements.get(id);
  }},
};
const code = fs.readFileSync(path.join(__dirname,'../static/app.js'),'utf8').replace(/init\(\);\s*$/, '');
vm.runInNewContext(code + `
  const paper = {id:'p',url:'javascript:alert(1)',title:'<img src=x onerror=alert(1)>',
    group:'science',groups:['science','papers'],type:'paper',tags:['materials'],
    source_ids:['zotero','alpha'],source_names:['Zotero','alphaXiv'],
    first_seen:'2026-10-08T23:30:00Z',published_at:'2026-10-01T00:00:00Z',
    excerpt:'crystal potential',summary:'<script>bad()</script>',summary_kind:'ai_summary',
    zotero_score:0.3,alpha_rank:4,authors:['A']};
  data = {items:[paper]}; days=0;
  assert.equal(localDay(paper.first_seen),'2026-10-09');
  assert.equal(safeURL(paper.url),'#');
  const markup = card(paper);
  assert.equal(markup.includes('<script>bad()'),false);
  assert.equal(markup.includes('<img src=x'),false);
  assert.equal(markup.includes('href="#"'),true);
  channel='papers';
  assert.equal(filtered().length,1);
  channel='science';
  assert.equal(filtered().length,1);
  channel=''; $('query').value='crystal';
  assert.equal(filtered().length,1);
  $('query').value='absent'; assert.equal(filtered().length,0);
  $('query').value=''; $('archive-date').value='2026-10-09';
  assert.equal(filtered().length,1);
  $('archive-date').value='2026-10-08'; assert.equal(filtered().length,0);
  $('archive-date').value=''; $('unread').checked=true; read.add('p');
  assert.equal(filtered().length,0);
  $('unread').checked=false; savedView=true; assert.equal(filtered().length,0);
  saved.add('p'); assert.equal(filtered().length,1);
  savedView=false; $('sort').value='zotero'; assert.equal(filtered().length,1);
  $('sort').value='alpha'; assert.equal(filtered().length,1);
  data.items.push({...paper,id:'other',source_ids:['hf-daily'],alpha_rank:undefined});
  assert.equal(filtered().length,1);
  $('sort').value='recent';
  const tree=[
    {id:'root',name:'<Science>',path:'<Science>',parent_id:null},
    {id:'child',name:'Materials',path:'<Science> / Materials',parent_id:'root'},
    {id:'leaf',name:'<img src=x onerror=alert(1)>',path:'<Science> / Materials / Leaf',parent_id:'child'},
  ];
  paper.topic_ids=['root','child','leaf']; paper.topic_leaf_ids=['leaf'];
  data={items:[paper,{...paper,id:'empty',topic_ids:[],topic_leaf_ids:[]}],taxonomy:{topics:tree}};
  topic='root'; assert.equal(filtered().length,1);
  topic='child'; assert.equal(filtered().length,1);
  topic='leaf'; assert.equal(filtered().length,1);
  topic='unclassified'; assert.equal(filtered().length,1);
  topic=''; assert.equal(filtered().length,2);
  const navigation=topicNavigation();
  assert.equal((navigation.match(/topic-branch/g)||[]).length,2);
  assert.equal(navigation.includes('<Science>'),false);
  assert.equal(navigation.includes('<img src=x'),false);
  assert.equal(navigation.includes('&lt;img src=x'),true);
  assert.equal(itemTopics(paper).includes('data-topic="leaf"'),true);
  assert.equal(itemTopics(paper).includes('<Science>'),false);
  assert.equal(itemTopics(data.items[1]).includes('主题待分类'),true);
`, sandbox);
console.log('Frontend behavior: 29 assertions passed (minimal DOM; not a browser deployment test)');
