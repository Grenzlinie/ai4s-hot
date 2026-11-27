// Focused search behavior only. Browser layout and assets are tested separately.
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),assert=require('node:assert/strict');
const elements=new Map();const context={assert,URL,Intl,Date,Set,Map,WeakMap,Number,JSON,console,
 location:{href:'https://local.test/'},history:{pushState(){},replaceState(){}},localStorage:{getItem:()=>null},
 document:{getElementById(id){if(!elements.has(id))elements.set(id,{value:'',checked:false,setAttribute(){}});return elements.get(id)}},setTimeout:()=>0,clearTimeout(){}};
const code=fs.readFileSync(path.join(__dirname,'../static/app.js'),'utf8').replace(/init\(\);\s*$/,'');
vm.runInNewContext(code+`
let checks=0;const failures=[];const check=(name,run)=>{checks++;try{run()}catch(error){failures.push(name+': '+error.message)}};
const base={excerpt:'',source_ids:['fixture'],source_names:['Fixture'],first_seen:'2026-11-27T00:00:00Z',published_at:'2026-11-27T00:00:00Z',group:'science',groups:['science'],type:'paper',authors:[],topic_ids:[],topic_leaf_ids:[]};
data={taxonomy:{topics:[]},sources:[],items:[
 {...base,id:'title',title:'Graph potentials for materials',authors:['Wei Li'],doi:'10.1038/s41563-026-00123-4',arxiv_id:'2601.12345',url:'https://www.nature.com/articles/s41563-026-00123-4',published_at:'2026-11-20T00:00:00Z'},
 {...base,id:'body',title:'Hydrogel study',authors:['Mei Wu'],excerpt:'Graph potentials for materials',url:'https://example.org/body'},
 {...base,id:'old',title:'Graph methods',authors:['Wei Li'],url:'https://example.org/old'},
 {...base,id:'report',title:'Graph methods report',authors:['Wei Li'],type:'report',content_kind:'web:technical_report',url:'https://example.org/report'}]};
days=0;const query=value=>{$('query').value=value;return filtered().map(p=>p.id)};
check('mixed title+author tokens AND',()=>assert.deepEqual(query('potentials Li'),['title']));
check('token order independent',()=>assert.deepEqual(query('Li potentials'),['title']));
check('missing token rejects result',()=>assert.deepEqual(query('potentials missing-author'),[]));
check('bare DOI',()=>assert.deepEqual(query('10.1038/s41563-026-00123-4'),['title']));
check('DOI URL regardless publisher landing URL',()=>assert.deepEqual(query('https://doi.org/10.1038/s41563-026-00123-4'),['title']));
check('arXiv bare identifier',()=>assert.deepEqual(query('2601.12345'),['title']));
check('arXiv abstract URL regardless stored landing URL',()=>assert.deepEqual(query('https://arxiv.org/abs/2601.12345'),['title']));
check('title evidence ranks above newer excerpt evidence',()=>assert.equal(query('Graph potentials')[0],'title'));
check('latest mode remains chronological',()=>{viewMode='latest';assert.equal(query('Graph potentials')[0],'body');viewMode='recommended'});
check('legacy paper type supports kind filter',()=>{kind='web:paper';assert.deepEqual(query('Graph Li').sort(),['old','title']);kind=''});
check('current explicit kind filter still applies',()=>{kind='web:technical_report';assert.deepEqual(query('Graph Li'),['report']);kind=''});
check('normalization handles full-width letters and case',()=>assert.deepEqual(query('ＧＲＡＰＨ potentials'),['title','body']));
check('short name parts cannot match substrings or different authors',()=>{
  const old=data.items;
  data.items=[
    {...base,id:'false',title:'Whole-Body Learning for Humanoids'},
    {...base,id:'split',title:'A materials study',authors:['Bo Yang','Xuming Hu']},
    {...base,id:'direct',title:'A materials study',authors:['Bo Hu']}];
  assert.deepEqual(query('Bo Hu'),['direct']);
  assert.ok(card(data.items[2]).includes('作者</span><mark class="query-hit">Bo Hu</mark>'));
  data.items=old;
});
check('search card shows original excerpt around a distant matching term',()=>{
  const row={...base,title:'Membranes',excerpt:'Prior context. '.repeat(40)+'The phase uses perovskite layers.',summary:'关于膜的进一步研究。'};
  query('perovskite');
  const markup=card(row);
  assert.ok(markup.includes('原始摘要</span>…'));
  assert.ok(markup.includes('<mark class="query-hit">perovskite</mark> layers'));
  assert.match(markup,/关于膜的进一步研究/);
});
check('title and author hits are visible and text is escaped',()=>{
  query('Graph Li');
  const markup=card({...data.items[0],title:'<script>Graph</script> potentials'});
  assert.ok(markup.includes('&lt;script&gt;<mark class="query-hit">Graph</mark>&lt;/script&gt;'));
  assert.ok(markup.includes('作者</span>Wei <mark class="query-hit">Li</mark>'));
  assert.doesNotMatch(markup,/<script>/);
});
check('identifier result highlights the stored canonical identifier',()=>{
  query('https://arxiv.org/abs/2601.12345v2');
  assert.ok(card(data.items[0]).includes('arXiv</span><mark class="query-hit">2601.12345</mark>'));
});
console.log('Manor search focused: '+(checks-failures.length)+'/'+checks+' passed');if(failures.length)throw Error(failures.join('\\n'));
`,context);
