// Owner preview only. Reads the existing local aggregate report; inserts no ratings.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {chromium}=require(require.resolve('playwright',{paths:[process.cwd(),process.cwd()+'/.runtime/browser']}));
const credentials=JSON.parse(readFileSync('.runtime/feedback-owner-credentials.json','utf8'));
const base='http://127.0.0.1:3000';
const browser=await chromium.launch({headless:true,...(process.env.CHROME_PATH?{executablePath:process.env.CHROME_PATH}:{})});
try{
 const anonymous=await browser.newContext();
 const denied=await anonymous.request.get(base+'/owner/feedback');
 assert.equal(denied.status(),401);assert.match(denied.headers()['www-authenticate'],/^Basic/);
 // Bypass CSP only in the audit browser so axe can be injected. Production
 // sends a script-free page with default-src 'none', checked below.
 const context=await browser.newContext({bypassCSP:true,httpCredentials:{username:credentials.username,password:credentials.password}});
 const page=await context.newPage();
 const response=await page.goto(base+'/owner/feedback');
 assert.equal(response.status(),200);
 assert.match(response.headers()['content-security-policy'],/default-src 'none'/);
 await page.getByRole('heading',{name:'Shared feedback',exact:true}).waitFor();
 await page.getByRole('heading',{name:'The six optional questions',exact:true}).waitFor();
 assert.ok(!await page.content().then(html=>html.includes(credentials.password)));
 const report=await context.request.get(base+'/owner/feedback?days=7&download=json');
 assert.equal(report.status(),200);const data=await report.json();assert.equal(data.days,7);
 assert.equal(Object.keys(data.quality_ratings).length,6);
 assert.equal(data.storage,'temporary');
 for(const format of ['json','html']){
  const result=await context.request.get(base+'/owner/feedback?download='+format);
  assert.match(result.headers()['content-disposition'],new RegExp('attachment;.*\\.'+format));
  assert.match(result.headers()['cache-control'],/no-store/);
 }
 await page.getByLabel('Report period').selectOption('7');
 await page.getByRole('button',{name:'Refresh report'}).click();
 assert.ok(page.url().includes('days=7'));
 for(const width of [1280,390,320]){
  await page.setViewportSize({width,height:900});
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
 }
 if(process.env.AXE_SCRIPT_PATH){
  await page.addScriptTag({path:process.env.AXE_SCRIPT_PATH});
  const violations=await page.evaluate(async()=>{const result=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa','best-practice']}});return result.violations.map(v=>v.id);});
  assert.deepEqual(violations,[]);
 }
 await page.screenshot({path:'.runtime/owner-feedback-preview.png',fullPage:true});
 console.log('Owner auth, six-question report, JSON/HTML downloads, period selection, mobile reflow and accessibility passed.');
}finally{await browser.close();}
