// Local browser regression: delayed config and HTTP failures are simulated;
// no source material, microphone audio or provider requests are sent.
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import path from 'node:path';
const require=createRequire(import.meta.url);
const {chromium}=require(require.resolve('playwright',{paths:[process.cwd(),path.resolve('.runtime/browser')]}));
const base=process.env.CONNECTION_TEST_URL||'http://127.0.0.1:3035';
assert.ok(['127.0.0.1','localhost'].includes(new URL(base).hostname));
const browser=await chromium.launch({headless:true,...(process.env.CHROME_PATH?{executablePath:process.env.CHROME_PATH}:{})});
try{
 const page=await browser.newPage();
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.clock.install();
 let requests=0;
 let pending;
 await page.route('**/api/**',route=>{
  assert.equal(new URL(route.request().url()).pathname,'/api/config');
  requests++;pending=route;
 });
 await page.goto(base);
 await page.waitForFunction(()=>!!document.querySelector('.connection-status'));
 await page.locator('#goal').fill('Keep my edited goal');
 await page.clock.fastForward(9000);
 await page.getByText('Still connecting to the rehearsal room…',{exact:true}).waitFor();
 assert.equal(await page.locator('.loading-clapper').count(),1);
 assert.equal(await page.locator('.loading-clapper').getAttribute('aria-hidden'),'true');
 assert.equal(await page.locator('.loading-clapper-lid').evaluate(node=>getComputedStyle(node).animationName),'rehearsal-clap');
 await page.emulateMedia({reducedMotion:'reduce'});
 assert.equal(await page.locator('.loading-clapper-lid').evaluate(node=>getComputedStyle(node).animationName),'none');
 await page.setViewportSize({width:390,height:844});
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 await page.evaluate(()=>window.scrollTo(0,0));
 await page.screenshot({path:'.runtime/loading-mobile.png'});
 assert.match(await page.locator('.connection-status').innerText(),/Waiting: 9 seconds/);
 assert.equal(await page.getByRole('button',{name:/Build my mission|Connecting…/}).isDisabled(),true);
 const first=pending;pending=null;
 await first.fulfill({status:504,body:'{}'});
 await page.getByText(/Retrying automatically once/).waitFor();
 // Wait for the retry request without making a real API call.
 await page.waitForResponse(()=>false,{timeout:100}).catch(()=>{});
 assert.equal(requests,2);
 await pending.fulfill({status:200,contentType:'application/json',body:JSON.stringify({mode:'demo'})});
 await page.locator('.connection-status').waitFor({state:'hidden'});
 assert.equal(await page.locator('#goal').inputValue(),'Keep my edited goal');
 assert.equal(await page.getByRole('button',{name:/Build my mission/}).isEnabled(),true);

 await page.unroute('**/api/**');
 requests=0;
 await page.route('**/api/config',route=>{
  requests++;
  return route.fulfill({status:requests<=2?503:200,contentType:'application/json',body:JSON.stringify({mode:'demo'})});
 });
 await page.reload();
 await page.getByRole('button',{name:'Retry connection',exact:true}).waitFor();
 await page.clock.fastForward(120000);
 assert.equal(requests,2,'Automatic retries must be bounded');
 await page.getByRole('button',{name:'Retry connection',exact:true}).click();
 await page.locator('.connection-status').waitFor({state:'hidden'});
 assert.equal(requests,3);

 await page.unroute('**/api/config');
 requests=0;
 await page.route('**/api/config',route=>{requests++;return route.fulfill({status:403,body:'{}'});});
 await page.reload();
 await page.getByRole('button',{name:'Retry connection',exact:true}).waitFor();
 assert.equal(requests,1,'Do not retry a permanent HTTP error automatically');
 assert.equal(await page.locator('.loading-clapper').count(),0,'Failed connections must stop animating');
 await page.unroute('**/api/config');
 let setupRequest;
 await page.route('**/api/**',route=>{
  if(new URL(route.request().url()).pathname==='/api/config')return route.fulfill({status:200,contentType:'application/json',body:'{"mode":"demo"}'});
  setupRequest=route;
 });
 await page.reload();
 await page.getByRole('button',{name:/Build my mission/}).click();
 await page.locator('.rehearsal-loading').getByText('Preparing your rehearsal…',{exact:true}).waitFor();
 assert.equal(await page.locator('.rehearsal-loading .loading-clapper').count(),1);
 await setupRequest.fulfill({status:400,contentType:'application/json',body:'{"detail":"Test source rejected."}'});
 await page.locator('.rehearsal-loading').waitFor({state:'hidden'});
 assert.deepEqual(errors,[]);
 console.log('PASS: startup feedback, bounded retry, preserved setup, manual recovery, permanent-error handling, clapperboard, mobile layout, reduced motion, action loading cleanup.');
}finally{await browser.close();}
