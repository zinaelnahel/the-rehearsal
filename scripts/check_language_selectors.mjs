// Regression: translated option labels must never change canonical select values.
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import fs from 'node:fs/promises';
import path from 'node:path';
const require=createRequire(import.meta.url);
const {chromium}=require(require.resolve('playwright',{paths:[process.cwd(),path.resolve('.runtime/browser')]}));
const browser=await chromium.launch({headless:true,...(process.env.CHROME_PATH?{executablePath:process.env.CHROME_PATH}:{})});
const base=process.env.REHEARSAL_TEST_URL||'http://127.0.0.1:3138';
const expectedSha=process.env.EXPECTED_FRONTEND_SHA;
const checks=[],errors=[];
const labels={en:{English:'English',German:'German',Spanish:'Spanish'},de:{English:'Englisch',German:'Deutsch',Spanish:'Spanisch'},es:{English:'Inglés',German:'Alemán',Spanish:'Español'}};
try{
 const page=await browser.newPage();page.setDefaultTimeout(15000);page.on('pageerror',e=>errors.push(e.message));
 let imported;
 await page.route('**/api/video/transcript',route=>{
  imported=route.request().postDataJSON();
  return route.fulfill({json:{segments:[{start:0,end:3,text:'Fictional caption fixture.'}],language:imported.language,
   source_url:imported.url,source_method:'youtube_captions',is_generated:false}});
 });
 await page.goto(base,{waitUntil:'networkidle'});
 assert.equal(await page.locator('.interface-language option[value=es]').innerText(),'Español');
 await page.locator('[role=tab]').nth(2).click();
 const url='https://www.youtube.com/watch?v=abcdefghijk';
 await page.locator('#video-url').fill(url);
 const consent=page.locator('.transcript-editor > .speech-consent input').first();await consent.check();
 for(const locale of ['en','de','es']){
  await page.locator('.interface-language select').selectOption(locale);
  for(const [index,language] of ['English','German','Spanish'].entries()){
   const feedback=['Spanish','English','German'][index],style=['Everyday','B1','B2'][index];
   await page.locator('#language').selectOption(language);
   await page.locator('#feedback').selectOption(feedback);
   await page.locator('#level').selectOption(style);
   assert.equal(await page.locator('#language').inputValue(),language);
   assert.equal(await page.locator('#language option:checked').innerText(),labels[locale][language]);
   assert.equal(await page.locator('#feedback').inputValue(),feedback);
   assert.equal(await page.locator('#feedback option:checked').innerText(),labels[locale][feedback]);
   assert.equal(await page.locator('#level').inputValue(),style);
   assert.equal(await page.locator('#video-url').inputValue(),url);
   assert.equal(await consent.isChecked(),true);
   await page.locator('.transcript-editor > button').first().click();
   await page.locator('.transcript-editor h3').waitFor();
   assert.equal(imported.language,await page.locator('#language').inputValue());
   assert.equal(imported.language,language);
   checks.push({locale,conversation:language,feedback,style,selected_label:labels[locale][language],caption_request:imported.language,passed:true});
  }
 }
 // Changing interface language again preserves all three selections.
 await page.locator('.interface-language select').selectOption('de');
 assert.equal(await page.locator('#language').inputValue(),'Spanish');
 assert.equal(await page.locator('#feedback').inputValue(),'German');
 assert.equal(await page.locator('#level').inputValue(),'B2');
 const config=await page.evaluate(()=>fetch('/api/config',{cache:'no-store'}).then(r=>r.json()));
 assert.ok('frontend_build_sha' in config&&'backend_build_sha' in config);
 if(expectedSha){
  assert.equal(config.frontend_build_sha,expectedSha);
  assert.ok((await page.locator('.build-info').innerText()).includes(expectedSha.slice(0,7)));
 }
 if(config.backend_build_sha){
  assert.match(config.backend_build_sha,/^[a-f0-9]{40}$/i);
  assert.ok((await page.locator('.build-info').innerText()).includes(config.backend_build_sha.slice(0,7)));
 }
 for(const width of [390,1280]){await page.setViewportSize({width,height:900});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));}
 assert.deepEqual(errors,[]);
 const report={passed:true,url:base,checks,spelling:'Español',builds:{frontend:config.frontend_build_sha,backend:config.backend_build_sha},
  provider_responses:'stubbed caption fixtures; real rendered controls and request serialization',sessions_created:0,page_errors:errors};
 await fs.mkdir('.runtime',{recursive:true});await fs.writeFile('.runtime/language-selectors.json',JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify(report,null,2));
}finally{await browser.close();}
