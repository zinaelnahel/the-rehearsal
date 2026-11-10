// Local UI integration check; APIs and embedded YouTube traffic are mocked.
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import path from 'node:path';
const require=createRequire(import.meta.url);
const {chromium}=require(require.resolve('playwright',{paths:[process.cwd(),path.resolve('.runtime/browser')]}));
const base=process.env.MEDIA_TEST_URL||'http://127.0.0.1:3032';
assert.ok(['localhost','127.0.0.1'].includes(new URL(base).hostname));
const browser=await chromium.launch({headless:true});
const page=await browser.newPage();
const url='https://www.youtube.com/watch?v=8YsZZpFW_QU';
const source={id:'20',url,start:79.27,end:85.25,text:'cuesta menos de mil euros',location:'79.27s–85.25s',source:'Reviewed video transcript'};
const goal={id:'0',text:'Ask about rent',achieved:false,answer_status:'not_asked'};
const errors=[];page.on('pageerror',error=>errors.push(error.message));
try{
 await page.route('https://www.youtube-nocookie.com/**',route=>route.fulfill({contentType:'text/html',body:'<p>Mock video player</p>'}));
 await page.route('**/api/**',route=>{
  const p=new URL(route.request().url()).pathname;
  const json=data=>route.fulfill({contentType:'application/json',body:JSON.stringify(data)});
  if(p==='/api/config')return json({mode:'live',speech_enabled:true});
  if(p==='/api/video/transcript')return json({segments:[{start:79.27,end:85.25,text:source.text}],source_url:url,source_method:'youtube_captions',notice:'Review the captions before use.'});
  if(p==='/api/sessions')return json({id:'video-test',source_url:url});
  if(p.endsWith('/mission'))return json({goals:[goal],safety:false});
  if(p.endsWith('/start'))return json({goals:[goal],safety:false,turns:[{id:'reply',role:'assistant',content:'El alquiler cuesta menos de mil euros. [20]',sources:[source]}]});
  if(route.request().method()==='DELETE')return json({deleted:true});
  if(p.endsWith('/status'))return route.fulfill({status:404,body:'{}'});
  throw Error('Unexpected API '+p);
 });
 await page.goto(base);
 await page.getByRole('tab',{name:'Audio / video',exact:true}).click();
 assert.equal(await page.locator('.video-import-details').getAttribute('open'),null);
 await page.locator('.video-import-details>summary').focus();await page.keyboard.press('Enter');
 assert.equal(await page.locator('.video-import-details p').isVisible(),true);
 await page.keyboard.press('Enter');
 assert.equal(await page.locator('.video-import-details p').isVisible(),false);
 await page.locator('#video-url').fill(url);
 await page.getByLabel('I agree to fetch this public video or its captions and send direct-video audio to OpenAI.').check();
 await page.getByRole('button',{name:'Import video transcript',exact:true}).click();
 await page.getByLabel('I reviewed this transcript and want to use it as my source.',{exact:true}).check();
 await page.getByRole('button',{name:/Build my mission/}).click();
 await page.getByRole('button',{name:/Action - start Take/}).click();
 await page.getByRole('button',{name:'Load source video'}).waitFor();
 assert.equal(await page.locator('.voice-rehearsal').getAttribute('open'),null);
 assert.equal(await page.locator('.help-panel').getAttribute('open'),null);
 assert.match(await page.locator('.goal-outcome').innerText(),/Not yet practised[\s\S]*Answer not checked/);
 await page.locator('.voice-rehearsal>summary').click();
 await page.getByRole('button',{name:'Start voice rehearsal'}).waitFor();
 assert.equal(await page.getByRole('button',{name:'Start voice rehearsal'}).isDisabled(),true);
 await page.locator('.voice-rehearsal>summary').click();
 await page.locator('.help-panel>summary').click();
 await page.getByRole('button',{name:/Help me/}).waitFor();
 await page.locator('.help-panel>summary').click();

 assert.equal(await page.locator('.source-video iframe').count(),0);
 await page.getByText(/▤ View source evidence/).click();
 await page.getByRole('button',{name:'Watch this part · 1:19'}).click();
 const frame=page.locator('.source-video iframe');await frame.waitFor();
 assert.match(await frame.getAttribute('src'),/start=79.*end=86/);
 assert.match(await page.locator('.source-video a').getAttribute('href'),/t=79s/);
 assert.match(await page.locator('.source-video').innerText(),/1:19–1:25/);
 await page.screenshot({path:'.runtime/practice-ux-desktop.png',fullPage:true});
 await page.setViewportSize({width:390,height:844});
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
 for(const [locale,label] of [['de','Diese Stelle ansehen · 1:19'],['es','Ver este fragmento · 1:19']]){
  await page.locator('.interface-language select').selectOption(locale);
  await page.getByRole('button',{name:label,exact:true}).click();
  assert.match(await frame.getAttribute('src'),/start=79.*end=86/);
 }
 await page.locator('.interface-language select').selectOption('en');
 await page.getByRole('button',{name:'End & delete session ↗',exact:true}).click();
 await page.locator('.deletion-notice').waitFor();
 assert.equal(await page.locator('.source-video iframe').count(),0);
 assert.deepEqual(errors,[]);
 console.log('PASS: source selection, timestamped embed/link, lazy loading, mobile width, deletion cleanup; network mocked.');
}finally{await browser.close();}
