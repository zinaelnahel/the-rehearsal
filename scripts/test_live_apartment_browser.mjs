// Opt-in real provider test. Never substitutes mocked replies for the live flow.
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {mkdirSync,writeFileSync} from 'node:fs';
const require=createRequire(import.meta.url);
const {chromium}=require(require.resolve('playwright',{paths:[process.cwd(),process.cwd()+'/.runtime/browser']}));
const base=process.env.LIVE_DEMO_URL;
assert.ok(['http://127.0.0.1:3000','https://the-rehearsal-lab.vercel.app'].includes(base),'Set LIVE_DEMO_URL explicitly; this test calls the real AI provider.');
const browser=await chromium.launch({headless:true,...(process.env.CHROME_PATH?{executablePath:process.env.CHROME_PATH}:{})});
const report={provider_backed:true,mocked:false,base,steps:[],passed:false};
let sid;
try{
 const page=await browser.newPage({viewport:{width:1280,height:960}});
 page.on('response',async response=>{
  const path=new URL(response.url()).pathname;
  if(path==='/api/sessions'&&response.request().method()==='POST'&&response.ok())sid=(await response.json()).id;
 });
 page.setDefaultTimeout(85000);
 await page.goto(base);
 const config=await (await page.request.get(base+'/api/config')).json();
 assert.equal(config.mode,'live');report.ui_build=config.frontend_build_sha;report.api_build=config.backend_build_sha;
 await page.locator('.theme-control select').selectOption('light');
 await page.getByRole('button',{name:/Habla con E/}).click();
 await page.getByRole('checkbox',{name:'I reviewed this transcript and want to use it as my source.',exact:true}).check();
 await page.locator('#feedback').selectOption('English');
 let start=Date.now();await page.getByRole('button',{name:'Build my mission'}).click();
 await page.getByRole('heading',{name:'Your conversation checklist'}).waitFor();
 report.steps.push({step:'mission',seconds:(Date.now()-start)/1000});
 // A short, repeatable graduation-demo path: one observable goal.
 while(await page.locator('.edit-goal').count()>1)await page.getByRole('button',{name:'Remove goal '+await page.locator('.edit-goal').count(),exact:true}).click();
 await page.locator('#goal0').fill('Ask about the monthly rent and included bills for the flat being viewed');
 mkdirSync('.runtime/live-demo',{recursive:true});
 await page.screenshot({path:'.runtime/live-demo/plan.png',fullPage:true});
 await page.getByRole('button',{name:/Action - start Take 01/}).click();
 await page.locator('#message').fill('¿Cuánto cuesta el alquiler al mes y qué gastos están incluidos?');
 const turnResponse=page.waitForResponse(r=>new URL(r.url()).pathname.endsWith('/turn')&&r.request().method()==='POST');
 start=Date.now();await page.getByRole('button',{name:'Send message',exact:true}).click();
 const response=await turnResponse;const turn=await response.json();
 report.steps.push({step:'turn',seconds:(Date.now()-start)/1000,status:response.status()});
 assert.equal(response.status(),200,JSON.stringify(turn));
 assert.equal(turn.turn.answer_withheld,false,'A withheld reply is not a successful factual demo');
 assert.match(turn.turn.content,/mil|1[., ]?000|1000/i);assert.match(turn.turn.content,/gas/i);assert.match(turn.turn.content,/agua/i);
 assert.ok(turn.turn.sources.length);report.reply=turn.turn;
 await page.waitForFunction(()=>!document.querySelector('.rehearsal-loading'));
 assert.equal(await page.locator('.message.user').count(),1);
 await page.screenshot({path:'.runtime/live-demo/reply.png',fullPage:true});
 start=Date.now();await page.getByRole('button',{name:/Cut - finish/}).click();
 await page.getByRole('heading',{name:'What you made happen'}).waitFor();
 report.steps.push({step:'review',seconds:(Date.now()-start)/1000});
 assert.ok(await page.locator('.feedback-item').count());
 assert.match(await page.locator('.feedback-item').first().innerText(),/Cuánto cuesta/);
 await page.screenshot({path:'.runtime/live-demo/review.png',fullPage:true});
 report.passed=true;
 console.log(JSON.stringify({provider_backed:true,passed:true,steps:report.steps}));
}finally{
 if(sid){const context=await browser.newContext();const deleted=await context.request.delete(base+'/api/sessions/'+sid);report.session_deleted=deleted.ok();}
 mkdirSync('.runtime',{recursive:true});writeFileSync('.runtime/live-demo-report.json',JSON.stringify(report,null,2));await browser.close();
}
