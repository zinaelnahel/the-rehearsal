// Source review integration: application APIs and YouTube are mocked.
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import path from 'node:path';
const require=createRequire(import.meta.url);
const {chromium}=require(require.resolve('playwright',{paths:[process.cwd(),path.resolve('.runtime/browser')]}));
const base=process.env.MEDIA_TEST_URL||'http://127.0.0.1:3034';
assert.ok(['localhost','127.0.0.1'].includes(new URL(base).hostname));
const browser=await chromium.launch({headless:true});
const page=await browser.newPage();
const errors=[];page.on('pageerror',error=>errors.push(error.message));
const videoUrl='https://www.youtube.com/watch?v=Q4asZ6JDy-w';
const segments=Array.from({length:45},(_,index)=>({start:600+index*5,end:604+index*5,text:index===0?'Lesson introduction.':'Caption '+index}));
let kind='video',created=[],sourceReads=0,serial=0;
const goal={id:'0',text:'Ask about rent',achieved:false,answer_status:'not_asked'};
const focus=()=>kind==='video'?{id:'1',text:'Selected dialogue',source:'Reviewed video transcript',location:'695s–699s',url:videoUrl,start:695,end:699}:{id:'2',text:'Nearby information. The rent is 1200 dollars. Other details.',highlights:['The rent is 1200 dollars.'],source:kind==='pdf'?'flat.pdf':'Pasted document',location:kind==='pdf'?'Page 2':'Section 2'};
async function build(){await page.getByRole('button',{name:/Build my mission/}).click();await page.locator('.edit-goal').first().waitFor();}
async function start(){await page.getByRole('button',{name:/Action - start Take/}).click();await page.locator('.message.assistant').waitFor();}
async function end(){await page.getByRole('button',{name:'End & delete session ↗',exact:true}).click();await page.locator('.deletion-notice').waitFor();}
try{
 await page.addInitScript(()=>{window.revokedSourceUrls=[];const original=URL.revokeObjectURL;URL.revokeObjectURL=value=>{window.revokedSourceUrls.push(value);original(value);};});
 await page.route('https://www.youtube-nocookie.com/**',route=>route.fulfill({contentType:'text/html',body:'Mock video'}));
 await page.route(base+'/api/**',route=>{
  const request=route.request(),p=new URL(request.url()).pathname;
  const json=data=>route.fulfill({contentType:'application/json',body:JSON.stringify(data)});
  if(p==='/api/config')return json({mode:'live',speech_enabled:false});
  if(p==='/api/video/transcript')return json({source_url:videoUrl,source_method:'youtube_captions',notice:'Review before use.',segments});
  if(p==='/api/sessions'){created.push(request.postDataJSON());return json({id:'source-'+(++serial),source_url:kind==='video'?videoUrl:null});}
  if(p==='/api/upload')return json({id:'source-'+(++serial),name:'flat.pdf'});
  if(p.endsWith('/mission'))return json({scenario:'apartment',goals:[goal],safety:false});
  if(p.endsWith('/start'))return json({goals:[goal],safety:false,turns:[{id:'reply',role:'assistant',content:'A source-backed reply. ['+focus().id+']',sources:[focus()]}]});
  if(p.endsWith('/finish'))return json({goals:[{...goal,achieved:true,answer_status:'confirmed',evidence:'What is the rent?',answer_evidence:focus().text,answer_sources:[focus().id]}],feedback:[],unanswered:[],phrases:[],note:'Test review.'});
  if(p.includes('/source/')){sourceReads++;return json({kind:kind==='pdf'?'pdf':'text',focus:focus(),page:kind==='pdf'?2:null,sections:[{location:focus().location,text:'Context before. '+focus().text+' Context after. <img src=x onerror="window.sourceInjected=true">',selected:true}]});}
  if(request.method()==='DELETE')return json({deleted:true});
  if(p.endsWith('/status'))return route.fulfill({status:404,body:'{}'});
  throw Error('Unexpected API '+p);
 });
 await page.goto(base);
 await page.getByRole('tab',{name:'Audio / video',exact:true}).click();
 await page.locator('#video-url').fill(videoUrl);
 await page.getByLabel('I agree to fetch this public video or its captions and send direct-video audio to OpenAI.').check();
 await page.getByRole('button',{name:'Import video transcript',exact:true}).click();
 const confirmation=page.getByLabel('I reviewed this transcript and want to use it as my source.',{exact:true});
 await page.getByRole('button',{name:'Use this section',exact:true}).nth(5).click();
 await confirmation.check();
 await page.getByRole('button',{name:'Use full transcript',exact:true}).click();
 assert.equal(await confirmation.isChecked(),false);
 await page.getByRole('button',{name:'Start here',exact:true}).nth(19).click();
 await page.getByRole('button',{name:'Next transcript page',exact:true}).click();
 await page.locator('.transcript-editor textarea:not(#pasted-video-transcript)').first().fill('Edited dialogue caption 20.');
 await confirmation.check();
 await page.getByRole('button',{name:'End here',exact:true}).nth(1).click();
 assert.equal(await confirmation.isChecked(),false);
 assert.match(await page.locator('.caption-scope').innerText(),/3 timestamp blocks/);
 await confirmation.check();await build();
 assert.deepEqual(created[0].transcript.map(s=>s.start),[695,700,705]);
 assert.equal(created[0].transcript[1].text,'Edited dialogue caption 20.');
 assert.equal(JSON.stringify(created[0]).includes('Lesson introduction'),false);
 await page.getByRole('button',{name:'Back to source material',exact:true}).click();
 assert.match(await page.locator('.caption-scope').innerText(),/3 timestamp blocks/);
 assert.equal(await confirmation.isChecked(),true);
 await page.getByRole('button',{name:'Return to plan',exact:true}).click();
 await start();
 await page.getByRole('button',{name:'View source [1]',exact:true}).click();
 await page.locator('.source-video iframe').waitFor();
 await page.getByText(/▤ View source evidence/).click();
 await page.getByRole('button',{name:'View source',exact:true}).click();
 await page.locator('.source-video iframe').waitFor();
 assert.match(await page.locator('.source-video iframe').getAttribute('src'),/start=695/);
 assert.equal(sourceReads,0,'Video source uses its timestamp without fetching document context');
 await end();

 kind='text';await page.getByRole('tab',{name:'Your situation',exact:true}).click();
 await page.locator('#document').fill('Context before.\nThe rent is 1200 dollars.\nContext after.');
 await build();await start();await page.getByText(/▤ View source evidence/).click();
 assert.equal(sourceReads,0,'Source context is loaded only on request');
 await page.getByRole('button',{name:'View source',exact:true}).click();
 const dialog=page.getByRole('dialog');
 await dialog.locator('mark').waitFor();
 assert.equal(await dialog.locator('mark').innerText(),focus().highlights[0]);
 assert.match(await dialog.innerText(),/Context before.*Context after/s);
 assert.equal(await page.evaluate(()=>window.sourceInjected),undefined);
 assert.equal(await dialog.locator('img').count(),0,'Source markup is displayed as text');
 await page.keyboard.press('Escape');
 await page.waitForFunction(()=>document.activeElement?.textContent==='View source');
 for(const [locale,label,close] of [['de','Quelle ansehen','Quelle schließen'],['es','Ver fuente','Cerrar fuente']]){
  await page.locator('.interface-language select').selectOption(locale);
  await page.getByRole('button',{name:label,exact:true}).click();
  await dialog.locator('mark').waitFor();
  await page.getByRole('button',{name:close,exact:true}).click();
 }
 await page.locator('.interface-language select').selectOption('en');
 await page.getByRole('button',{name:/Cut - finish & reflect/}).click();
 await page.getByRole('button',{name:'View source [2]',exact:true}).click();
 await dialog.locator('mark').waitFor();
 assert.equal(await dialog.locator('mark').innerText(),focus().highlights[0]);
 await page.getByRole('button',{name:'Close source',exact:true}).click();
 await end();

 kind='pdf';await page.locator('#situation-source-kind').selectOption('file');
 await page.locator('#upload').setInputFiles({name:'flat.pdf',mimeType:'application/pdf',buffer:Buffer.from('%PDF-1.4\n%%EOF')});
 await build();await start();await page.getByText(/▤ View source evidence/).click();
 await page.getByRole('button',{name:'View source',exact:true}).click();
 await dialog.locator('mark').waitFor();
 assert.equal(await dialog.locator('.source-document-text h3').innerText(),'Page 2');
 await page.getByRole('button',{name:'View original PDF',exact:true}).click();
 await dialog.locator('iframe').waitFor();
 assert.match(await dialog.locator('iframe').getAttribute('src'),/^blob:.*#page=2$/);
 await page.setViewportSize({width:390,height:844});
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
 await page.getByRole('button',{name:'Close source',exact:true}).click();
 await page.waitForFunction(()=>window.revokedSourceUrls.length>0);
 await end();
 assert.equal(await page.locator('.source-document').count(),0);
 assert.deepEqual(errors,[]);
 console.log('PASS: cross-page caption selection, confirmation invalidation, selected-only payload, video timestamps, text highlight, PDF page/blob cleanup, keyboard focus, EN/DE/ES, mobile, deletion; APIs mocked.');
}finally{await browser.close();}
