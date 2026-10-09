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
`, sandbox);
console.log('Frontend behavior: 17 assertions passed (minimal DOM; not a browser deployment test)');
