// Source navigation + real local multipart proxy/FFmpeg; only the speech provider is stubbed.
// Run with scripts/media_test_backend.py and Next on MEDIA_TEST_URL, or provide
// an equivalent local speech-provider stub. Never point this at a paid live API.
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import path from 'node:path';
const require=createRequire(import.meta.url);
const {chromium}=require(require.resolve('playwright',{paths:[process.cwd(),path.resolve('.runtime/browser')]}));
const base=process.env.MEDIA_TEST_URL||'http://127.0.0.1:3031';
assert.ok(['127.0.0.1','localhost'].includes(new URL(base).hostname),'Use a local provider-stub backend.');
const browser=await chromium.launch({headless:true,...(process.env.CHROME_PATH?{executablePath:process.env.CHROME_PATH}:{})});
const page=await browser.newPage();
const errors=[];page.on('pageerror',error=>errors.push(error.message));
const goal={id:'0',text:'Ask about the rent',achieved:false,answer_status:'not_asked'};
let serial=0,imports=0,uploads=0;
const created=[];
try{
 await page.addInitScript(()=>Object.defineProperty(navigator,'mediaDevices',{value:{
  getUserMedia:async()=>{throw new DOMException('Requested device not found','NotFoundError');}}}));
 await page.route('**/api/**',async route=>{
  const request=route.request(),url=new URL(request.url()),p=url.pathname;
  const json=data=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(data)});
  if(p==='/api/speech/transcribe'){uploads++;return route.continue();}
  if(p==='/api/config')return json({mode:'live',speech_enabled:true,feedback_enabled:false,vector_store:'memory'});
  if(p==='/api/video/transcript'){
   imports++;
   return json({language:'English',source_url:'https://www.youtube.com/watch?v=UsHhxuOnlj8',
    source_method:'youtube_captions',notice:'Review the captions before use.',
    segments:[{start:0,end:2,text:'The rent is 850 euros.'},{start:2,end:4,text:'Council tax is extra.'}]});
  }
  if(p==='/api/sessions'){created.push(request.postDataJSON());return json({id:'test-'+(++serial),name:'Reviewed media'});}
  if(p.endsWith('/mission'))return json({goals:[goal],safety:false});
  if(request.method()==='DELETE')return json({deleted:true});
  if(p.endsWith('/status'))return route.fulfill({status:404,body:'{}'});
  throw Error('Unexpected test request '+p);
 });
 await page.goto(base);
 await page.getByRole('tab',{name:'Audio / video',exact:true}).click();
 await page.locator('#video-url').fill('https://www.youtube.com/watch?v=UsHhxuOnlj8');
 await page.getByLabel('I agree to fetch this public video or its captions and send direct-video audio to OpenAI.').check();
 await page.getByRole('button',{name:'Import video transcript',exact:true}).click();
 await page.getByRole('heading',{name:'Review the video transcript',exact:true}).waitFor();
 const editor=page.locator('.transcript-editor');
 await editor.locator('textarea:not(#pasted-video-transcript)').last().fill('Reviewed: council tax is extra.');
 const confirmation=page.getByLabel('I reviewed this transcript and want to use it as my source.',{exact:true});
 await confirmation.check();
 await page.getByRole('button',{name:/Build my mission/}).click();
 await page.locator('.edit-goal').first().waitFor();
 console.log('PASS initial video mission');
 assert.equal(await page.locator('#video-url').isVisible(),false);
 assert.equal(await page.evaluate(()=>document.activeElement?.textContent?.includes('Make it')),true);
 await page.getByRole('button',{name:'Back to source material',exact:true}).click();
 assert.equal(await page.locator('#video-url').inputValue(),'https://www.youtube.com/watch?v=UsHhxuOnlj8');
 assert.equal(await editor.locator('textarea:not(#pasted-video-transcript)').last().inputValue(),'Reviewed: council tax is extra.');
 assert.equal(await confirmation.isChecked(),true);
 await page.getByRole('button',{name:/Build my mission/}).click();
 await page.locator('.edit-goal').first().waitFor();
 assert.equal(imports,1);
 assert.equal(created.length,2);
 assert.equal(created[1].transcript[1].text,'Reviewed: council tax is extra.');
 console.log('PASS video navigation and rebuild without reimport');
 await page.getByRole('button',{name:'End & delete session ↗',exact:true}).click();
 await page.locator('.deletion-notice').waitFor();
 assert.equal(await page.locator('#video-url').inputValue(),'');
 assert.equal(await page.getByRole('heading',{name:'Review the video transcript'}).count(),0);
 console.log('PASS deletion clears source draft');

 await page.locator('#media-source-kind').selectOption('upload');
 await page.getByLabel('I agree to audio processing for transcription.').check();
 await page.getByRole('button',{name:'Record a voice message',exact:true}).click();
 await page.getByRole('alert').filter({hasText:'No microphone was found.'}).waitFor();
 // A synthetic 1-second PCM WAV exercises browser -> Next proxy -> FastAPI -> FFmpeg.
 const wav=Buffer.alloc(44+32000);wav.write('RIFF',0);wav.writeUInt32LE(wav.length-8,4);
 wav.write('WAVEfmt ',8);wav.writeUInt32LE(16,16);wav.writeUInt16LE(1,20);wav.writeUInt16LE(1,22);
 wav.writeUInt32LE(16000,24);wav.writeUInt32LE(32000,28);wav.writeUInt16LE(2,32);wav.writeUInt16LE(16,34);
 wav.write('data',36);wav.writeUInt32LE(32000,40);
 for(let i=0;i<16000;i++)wav.writeInt16LE(Math.round(10000*Math.sin(2*Math.PI*440*i/16000)),44+2*i);
 await page.locator('.speech-controls input[type=file]').setInputFiles({name:'synthetic.wav',mimeType:'audio/wav',buffer:wav});
 await page.getByRole('heading',{name:'Review the source transcript',exact:true}).waitFor();
 assert.match(await page.locator('.transcript-editor textarea').first().inputValue(),/850 euros/);
 await page.getByLabel('I reviewed this transcript and want to use it as my source.',{exact:true}).check();
 await page.getByRole('button',{name:/Build my mission/}).click();
 await page.locator('.edit-goal').first().waitFor();
 await page.getByRole('button',{name:'Back to source material',exact:true}).click();
 assert.equal(await page.locator('#media-source-kind').inputValue(),'upload');
 assert.match(await page.locator('.transcript-editor textarea').first().inputValue(),/850 euros/);
 assert.equal(await page.getByLabel('I reviewed this transcript and want to use it as my source.',{exact:true}).isChecked(),true);
 assert.equal(uploads,1);
 assert.deepEqual(errors,[]);
 console.log('PASS: video draft/confirmation retained, no reimport, end clears draft, missing microphone explained, real local multipart/FFmpeg upload and audio draft retained; provider stubbed.');
}finally{await browser.close();}
