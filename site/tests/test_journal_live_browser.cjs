/* Read-only browser acceptance against actual served archive/assets. No routes or fixtures. */
const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const base=process.argv[2];if(!base)throw Error('Usage: node test_journal_live_browser.cjs BASE_URL [OUTPUT_DIR]');
const out=path.resolve(process.argv[3]||process.env.JOURNAL_TEST_OUTPUT||require('node:os').tmpdir());fs.mkdirSync(out,{recursive:true});
const checks=[],errors=[],meta={base,captured_at:new Date().toISOString(),fixture:false,checks,errors};
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex'),ids=rows=>[...new Set(rows.map(p=>p.id))].sort();
const pending=p=>Boolean(p.journal_id&&p.journal_relevance?.status==='pending');
const required=['Nature Materials','Nature','Science','Nature Communications','Science Advances','Advanced Materials','Advanced Energy Materials','Advanced Functional Materials','Acta Materialia','Matter'];
(async()=>{let browser;try{
 browser=await chromium.launch({...(process.env.CHROME_PATH?{executablePath:process.env.CHROME_PATH}:{}),headless:true});
 const context=await browser.newContext({viewport:{width:1440,height:1000}}),page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
 async function fetchFile(name){const response=await context.request.get(new URL(name,base).href);assert.ok(response.ok(),name+' HTTP '+response.status());return response.body();}
 const raw=await fetchFile('data/index.json'),archive=JSON.parse(raw),manifest=JSON.parse(await fetchFile('deployment-manifest.json'));
 Object.assign(meta,{manifest,index_sha256:sha(raw),item_count:archive.items.length,journal_count:archive.journals?.length,journal_items:archive.items.filter(p=>p.journal_id).length,relevant:archive.items.filter(p=>p.journal_id&&!pending(p)).length,pending:archive.items.filter(pending).length});
 async function check(name,fn){try{await fn();checks.push({name,passed:true});}catch(e){checks.push({name,passed:false,error:e.message});}console.log(JSON.stringify(checks.at(-1)));}
 await check('manifest binds actual archive bytes, count and timestamp',async()=>{assert.equal(sha(raw),manifest.archive_sha256);assert.equal(archive.items.length,manifest.item_count);assert.equal(archive.generated_at,manifest.archive_generated_at);if(process.env.EXPECTED_CODE_REVISION)assert.equal(manifest.code_revision,process.env.EXPECTED_CODE_REVISION);});
 await check('manifest binds served frontend asset bytes',async()=>{for(const name of ['index.html','app.js','style.css'])assert.equal(sha(await fetchFile(name)),manifest.assets[name],name);});
 await check('all ten real journal titles registered',async()=>assert.deepEqual(archive.journals.map(j=>j.title).sort(),[...required].sort()));
 const visible=archive.items.filter(p=>!pending(p)),journalArticles=archive.items.filter(p=>p.journal_id&&!pending(p));
 await check('real related journal articles classified in shared topic catalog',async()=>{assert.ok(journalArticles.length>0,'No relevant journal articles');assert.ok(journalArticles.every(p=>typeof p.topic_status==='string'||p.classification?.status),'Classification status missing');assert.ok(journalArticles.some(p=>(p.topic_labels||[]).length||(p.topic_ids||[]).length),'No journal topic assignments');});
 async function ready(){await page.waitForFunction(()=>document.querySelector('#result-count')?.textContent?.includes('条'));}
 async function go(query='?days=0'){await page.goto(new URL(query,base).href);await ready();}
 const actual=()=>page.evaluate(()=>filtered().map(p=>p.id).sort());
 const equal=async rows=>assert.deepEqual(await actual(),ids(rows));
 await go();await check('default unified stream hides only pending journal candidates',()=>equal(visible));
 await page.locator('#open-journals').click();await check('all ten journals selectable even with zero results',async()=>assert.equal(await page.locator('#all-journals [data-journal]').count(),10));
 const chosen=[...new Set(journalArticles.map(p=>p.journal_id))].slice(0,2);if(chosen.length<2)chosen.push(archive.journals.find(j=>j.id!==chosen[0]).id);meta.selected_journals=chosen;
 for(const id of chosen)await page.locator(`#all-journals [data-journal="${id}"]`).click();
 const selection=visible.filter(p=>chosen.includes(p.journal_id));await check('multiple journal selections use OR on actual archive',()=>equal(selection));
 await page.keyboard.press('Escape');await page.waitForFunction(()=>document.activeElement.id==='open-journals');
 const copiedURL=page.url();await page.goto(copiedURL);await ready();await check('copied journal URL restores exact scope',()=>equal(selection));
 await page.locator('#latest').click();await check('latest preserves actual journal scope',()=>equal(selection));
 // Independent public taxonomy ancestor closure, not application matching code.
 const topics=archive.taxonomy?.topics||[],byID=new Map(topics.map(t=>[t.id,t]));
 const assigned=p=>{const out=new Set();for(let id of (p.topic_labels||[]).length?p.topic_labels.map(l=>l.label_id||l.id):(p.topic_leaf_ids||p.topic_ids||[])){const seen=new Set();while(id&&!seen.has(id)){out.add(id);seen.add(id);id=byID.get(id)?.parent_id;}}return out;};
 const topic=selection.flatMap(p=>[...assigned(p)]).find(id=>byID.has(id));
 await check('journal and existing research topic intersect on actual archive',async()=>{assert.ok(topic,'No public topic to exercise');const url=new URL(copiedURL);url.searchParams.set('topics',topic);await page.goto(url.href);await ready();await equal(selection.filter(p=>assigned(p).has(topic)));});
 await go('?days=0&journal_review=pending');await check('pending view contains exactly actual pending journal articles',()=>equal(archive.items.filter(pending)));
 await check('pending explanation is visible and readable',async()=>{assert.ok(await page.locator('#journal-review-note').isVisible());assert.match(await page.locator('#journal-review-note').innerText(),/相关性证据不足/);});
 await go();await page.locator('#health-toggle').click();await check('actual journal source health counters are visible',async()=>{const count=archive.sources.filter(s=>s.kind==='journal'&&s.counters).length;assert.equal(await page.locator('.journal-health-counts').count(),count);assert.ok(count>0);});
 for(const width of [1440,390]){await page.setViewportSize({width,height:1000});await go(copiedURL);await page.evaluate(async()=>{await document.fonts.ready;await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));});await page.waitForTimeout(100);await check(width+' layout has no horizontal overflow',async()=>assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true));await page.screenshot({path:path.join(out,'journal-real-'+width+'.png'),fullPage:false});await page.locator('#open-journals').click();await check(width+' dialog focuses search',async()=>assert.equal(await page.evaluate(()=>document.activeElement.id),'journal-search'));await page.keyboard.press('Escape');await page.waitForFunction(()=>document.activeElement.id==='open-journals');}
 await check('manifest unchanged throughout browser acceptance',async()=>assert.deepEqual(JSON.parse(await fetchFile('deployment-manifest.json')),manifest));
 await check('no browser JavaScript errors',async()=>assert.deepEqual(errors,[]));
 }catch(e){errors.push(e.stack||e.message);}finally{if(browser)await browser.close();meta.completed_at=new Date().toISOString();meta.passed=errors.length===0&&checks.length>0&&checks.every(c=>c.passed);fs.writeFileSync(path.join(out,'journal-real-browser.json'),JSON.stringify(meta,null,2)+'\n');if(!meta.passed)process.exitCode=1;console.log(JSON.stringify({passed:meta.passed,checks:checks.length,output:out}));}})();
