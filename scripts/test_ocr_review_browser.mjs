// OCR review workflow; all API responses are mocked, no recognition/model calls.
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import path from 'node:path';
const require=createRequire(import.meta.url);
const {chromium}=require(require.resolve('playwright',{paths:[process.cwd(),path.resolve('.runtime/browser')]}));
const base=process.env.MEDIA_TEST_URL||'http://127.0.0.1:3035';
assert.ok(['localhost','127.0.0.1'].includes(new URL(base).hostname));
const browser=await chromium.launch({headless:true});const page=await browser.newPage();
let uploads=0,missions=0,reviewed;
const deleted=[];const errors=[];page.on('pageerror',error=>errors.push(error.message));
try{
 await page.route(base+'/api/**',route=>{
  const request=route.request(),p=new URL(request.url()).pathname;
  const json=data=>route.fulfill({contentType:'application/json',body:JSON.stringify(data)});
  if(p==='/api/config')return json({mode:'live',speech_enabled:false});
  if(p==='/api/upload')return json({id:'ocr-'+(++uploads),name:'scan.pdf',requires_confirmation:true,source_method:'pdf_ocr',pages:[{location:'Page 1',text:'Rent is 2,40O euros.',ocr:true},{location:'Page 2',text:'Available December 2026.',ocr:true}]});
  if(p.endsWith('/source-review')){reviewed=request.postDataJSON();return json({id:'reviewed',name:'scan.pdf',import_method:'reviewed_pdf_ocr'});}
  if(p.endsWith('/mission')){missions++;return json({scenario:'apartment',goals:[{id:'0',text:'Ask about rent',achieved:false,answer_status:'not_asked'}],safety:false});}
  if(request.method()==='DELETE'){deleted.push(p);return json({deleted:true});}
  if(p.endsWith('/status'))return route.fulfill({status:404,body:'{}'});
  throw Error('Unexpected API '+p);
 });
 await page.goto(base);
 const privacy=page.locator('.privacy');
 await privacy.getByText(/Live mode sends retrieved text and your conversation to OpenAI/).waitFor();
 assert.equal(await privacy.locator('details').getAttribute('open'),null);
 await privacy.locator('summary').focus();await page.keyboard.press('Enter');
 assert.equal(await privacy.getByText(/Conversations stay in memory/).isVisible(),true);
 await page.keyboard.press('Enter');
 assert.equal(await privacy.getByText(/Conversations stay in memory/).isVisible(),false);
 await page.getByRole('tab',{name:'Your situation',exact:true}).click();
 assert.deepEqual(await page.locator('#situation-source-kind option').evaluateAll(options=>options.map(option=>option.value)),['text','file']);
 await page.locator('#situation-source-kind').selectOption('file');
 await page.locator('#upload').setInputFiles({name:'scan.pdf',mimeType:'application/pdf',buffer:Buffer.from('%PDF-fixture')});
 await page.getByRole('button',{name:/Build my mission/}).click();
 const dialog=page.getByRole('dialog');await dialog.waitFor();
 assert.equal(missions,0,'OCR cannot call the mission model before review');
 const use=page.getByRole('button',{name:'Use reviewed text and build mission',exact:true});
 assert.equal(await use.isDisabled(),true);
 await page.getByLabel('I reviewed this OCR text and want to use it as my source.',{exact:true}).check();
 await page.locator('#ocr-page-text').fill('Rent is 2,400 euros.');
 assert.equal(await use.isDisabled(),true,'Editing invalidates confirmation');
 await page.getByRole('button',{name:'Next PDF page',exact:true}).click();
 assert.equal(await page.locator('#ocr-page-text').inputValue(),'Available December 2026.');
 await page.getByRole('button',{name:'Previous PDF page',exact:true}).click();
 assert.equal(await page.locator('#ocr-page-text').inputValue(),'Rent is 2,400 euros.');
 await page.setViewportSize({width:390,height:844});
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
 await page.getByRole('button',{name:'Cancel document import',exact:true}).click();
 await dialog.waitFor({state:'hidden'});
 assert.equal(missions,0);assert.ok(deleted.includes('/api/sessions/ocr-1'));
 await page.getByRole('button',{name:/Build my mission/}).click();await dialog.waitFor();
 await page.keyboard.press('Escape');await dialog.waitFor({state:'hidden'});
 assert.ok(deleted.includes('/api/sessions/ocr-2'));
 await page.getByRole('button',{name:/Build my mission/}).click();await dialog.waitFor();
 await page.locator('#ocr-page-text').fill('Rent is 2,400 euros.');
 await page.getByLabel('I reviewed this OCR text and want to use it as my source.',{exact:true}).check();
 await use.click();await page.locator('.edit-goal').first().waitFor();
 assert.equal(missions,1);
 assert.equal(await page.locator('.scene-card').getByText('Source: uploaded PDF; OCR text reviewed by you.',{exact:true}).count(),1);
 assert.equal(await page.locator('.scene-card').getByText(/public-page snapshot/).count(),0);
 const goalInput=page.locator('.edit-goal input').first();
 const start=page.getByRole('button',{name:/Action - start Take 01/});
 await goalInput.fill('Mission goal 1');assert.equal(await start.isDisabled(),true);
 await page.getByText('Write a specific goal in each field before starting. Replace placeholders such as Mission goal 1.',{exact:true}).waitFor();
 await goalInput.fill('   mission goal 2   ');assert.equal(await start.isDisabled(),true);
 await goalInput.fill('');assert.equal(await start.isDisabled(),true);
 await goalInput.fill('Ask about rent');assert.equal(await start.isEnabled(),true);
 const goalText=await page.locator('.edit-goal input').first().inputValue();
 assert.equal(await page.getByRole('textbox',{name:goalText,exact:true}).count(),1);
 assert.deepEqual(reviewed,{texts:['Rent is 2,400 euros.','Available December 2026.'],confirmed:true});
 assert.equal(await page.locator('.document-review').count(),0);
 await page.getByRole('button',{name:'End & delete session ↗',exact:true}).click();
 await page.locator('.deletion-notice').waitFor();
 assert.ok(deleted.includes('/api/sessions/reviewed'));
 assert.deepEqual(errors,[]);
 console.log('PASS: listing-link option removed; OCR review blocks mission calls, edits invalidate consent, pages retained, cancel/Escape delete previews, confirmed edits build once, mobile and cleanup.');
}finally{await browser.close();}
