// Real browser acceptance using public synthetic fixtures; no API requests.
const {chromium}=require('playwright');
const fs=require('fs'),assert=require('assert/strict'),path=require('path');
const root=path.resolve(__dirname,'../..');
const out=process.env.JOURNAL_TEST_OUTPUT||require('os').tmpdir();
(async()=>{const browser=await chromium.launch({...(process.env.CHROME_PATH?{executablePath:process.env.CHROME_PATH}:{}),headless:true});let checks=0;
const journals=['Nature Materials','Nature','Science','Nature Communications','Science Advances','Advanced Materials','Advanced Energy Materials','Advanced Functional Materials','Acta Materialia','Matter'].map((title,i)=>({id:'j'+i,title,issns:[],publisher:'Publisher'}));
const now=new Date().toISOString(),entry=(id,j,status='relevant')=>({id,title:'Machine learning for alloy discovery '+id,type:'paper',url:'https://example.org/'+id,excerpt:'Public metadata fixture.',first_seen:now,published_at:now,source_ids:['rss'],journal_id:j,journal_title:journals.find(x=>x.id===j)?.title,journal_relevance:{status,reason:'Public metadata evidence'},content_kind:'web:paper',domain_facets:['web:materials'],topic_ids:['materials']});
const data={schema_version:2,generated_at:now,journals,items:[entry('a','j0'),entry('b','j9'),entry('c','j0','pending')],sources:[{id:'rss',name:'Journal feeds',status:'ok',count:3}],taxonomy:{topics:[{id:'materials',name:'材料',path:'材料',parent_id:null}]},policy:{lookback_days:30,max_items_per_source:12},summaries:{status:'ok',generated:0}};
for(const width of [1440,390]){const page=await browser.newPage({viewport:{width,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.route('http://journal.test/**',route=>{const u=new URL(route.request().url());if(u.pathname==='/data/index.json')return route.fulfill({json:data});if(u.pathname==='/update-status.json')return route.fulfill({status:404,body:''});const file=path.join(root,'site/static',u.pathname==='/'?'index.html':u.pathname);return route.fulfill({body:fs.readFileSync(file),contentType:file.endsWith('.js')?'application/javascript':file.endsWith('.css')?'text/css':'text/html'});});
await page.goto('http://journal.test/');await page.waitForSelector('#open-journals');assert.equal(await page.locator('.entry').count(),2);checks++;
await page.locator('#open-journals').click();assert.equal(await page.locator('#all-journals button').count(),10);checks++;
await page.locator('#journal-search').fill('Functional');assert.equal(await page.locator('#all-journals button').count(),1);checks++;
await page.locator('#all-journals button').click();assert.equal(await page.locator('#result-count').innerText(),'0 条');checks++;assert.equal(await page.evaluate(()=>document.activeElement.dataset.journal),'j7');checks++;
await page.keyboard.press('Escape');await page.waitForFunction(()=>document.activeElement.id==='open-journals');assert.equal(await page.evaluate(()=>document.activeElement.id),'open-journals');checks++;
await page.locator('[data-clear-filter="journals"]').click();await page.locator('#journal-review').click();assert.equal(await page.locator('.entry').count(),1);assert.match(page.url(),/journal_review=pending/);checks++;
await page.locator('#latest').click();assert.equal(await page.locator('.entry').count(),1);checks++;
await page.locator('[data-save="c"]').click();await page.locator('#saved').click();assert.equal(await page.locator('.entry').count(),1);checks++;
await page.reload();await page.waitForSelector('#item-c');assert.equal(await page.locator('#saved').getAttribute('aria-pressed'),'true');checks++;
await page.locator('#clear').click();await page.locator('#home').click();await page.locator('#open-journals').click();await page.locator('#journal-search').fill('');await page.locator('#all-journals [data-journal="j0"]').click();await page.locator('#all-journals [data-journal="j9"]').click();await page.locator('#journal-close').click();assert.equal(await page.locator('.entry').count(),2);checks++;
assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);checks++;
await page.evaluate(()=>document.fonts.ready);await page.screenshot({path:path.join(out,'AI4S-Hot-journals-'+width+'.png'),fullPage:false});
assert.deepEqual(errors,[]);checks++;await page.close();}
await browser.close();console.log(JSON.stringify({checks,widths:[1440,390],fixture:true,production:false}));})().catch(e=>{console.error(e);process.exit(1)});
