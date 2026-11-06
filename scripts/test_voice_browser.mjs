// Optional integration check: install Playwright, or set PLAYWRIGHT_MODULE to its
// index.mjs. Uses actual browser recording/VAD/playback with synthetic local audio
// and mocked HTTP responses; it makes no provider calls.
import assert from 'node:assert/strict';
import {mkdtemp,writeFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {pathToFileURL} from 'node:url';

const {chromium}=await import(process.env.PLAYWRIGHT_MODULE?pathToFileURL(process.env.PLAYWRIGHT_MODULE).href:'playwright');
const origin=process.env.VOICE_TEST_URL||'http://localhost:3118';
const folder=await mkdtemp(path.join(tmpdir(),'rehearsal-voice-'));
function wav(seconds,sample){
  const rate=16000,count=Math.floor(seconds*rate),buffer=Buffer.alloc(44+count*2);
  buffer.write('RIFF',0);buffer.writeUInt32LE(buffer.length-8,4);buffer.write('WAVEfmt ',8);
  buffer.writeUInt32LE(16,16);buffer.writeUInt16LE(1,20);buffer.writeUInt16LE(1,22);
  buffer.writeUInt32LE(rate,24);buffer.writeUInt32LE(rate*2,28);buffer.writeUInt16LE(2,32);
  buffer.writeUInt16LE(16,34);buffer.write('data',36);buffer.writeUInt32LE(count*2,40);
  for(let i=0;i<count;i++)buffer.writeInt16LE(Math.round(sample(i/rate)*32767),44+i*2);
  return buffer;
}
const microphone=path.join(folder,'microphone.wav');
await writeFile(microphone,wav(30,time=>time>2&&time<3.4?Math.sin(time*Math.PI*440)*0.35:0));
const openingAudio=wav(0.4,time=>Math.sin(time*Math.PI*330)*0.12);
const replyAudio=wav(12,time=>Math.sin(time*Math.PI*330)*0.12);
const browser=await chromium.launch({headless:true,
  ...(process.env.CHROME_PATH?{executablePath:process.env.CHROME_PATH}:{}),
  args:['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream',
    '--use-file-for-fake-audio-capture='+microphone]
});
const page=await browser.newPage({permissions:['microphone'],viewport:{width:1280,height:1000}});
page.setDefaultTimeout(20000);
const errors=[],requests=[],turns=[];
let resolveTurn;
const validation=new Promise(resolve=>{resolveTurn=resolve;});
page.on('pageerror',error=>errors.push(error.message));
await page.addInitScript(()=>{
  window.voiceTestTracks=[];
  const getUserMedia=navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
  navigator.mediaDevices.getUserMedia=async constraints=>{
    const stream=await getUserMedia(constraints);
    window.voiceTestTracks.push(...stream.getTracks());
    return stream;
  };
});
const goal={id:'0',text:'Ask about the rent',achieved:false,answer_status:'not_asked'};
const checkedReply={id:'checked-reply',role:'assistant',content:'The rent is 850 euros per month. [1]',
  sources:[{id:'1',text:'Monthly rent: 850 euros.',location:'Paragraph 1',source:'Fictional listing'}]};
await page.route('**/api/**',async route=>{
  const request=route.request(),pathname=new URL(request.url()).pathname;
  const json=data=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(data)});
  requests.push({pathname,body:request.postData()});
  if(pathname==='/api/config')return json({mode:'live',speech_enabled:true,vector_store:'memory'});
  if(pathname==='/api/sessions')return json({id:'voice-browser-session',name:'Fictional listing',mode:'live'});
  if(pathname.endsWith('/mission'))return json({goals:[goal],safety:false});
  if(pathname.endsWith('/start'))return json({turns:[{id:'opening',role:'assistant',content:'What would you like to ask?',sources:[]}],goals:[goal],safety:false});
  if(pathname==='/api/speech/transcribe'){
    assert.match(request.headers()['content-type'],/multipart\/form-data/);
    assert.match(request.postDataBuffer().toString('latin1'),/voice-turn\.webm/);
    return json({text:'How much is the rent?',language:'English',requires_confirmation:true});
  }
  if(pathname.endsWith('/turn')){
    turns.push(request.postDataJSON());
    await validation;
    return json({turn:checkedReply,goals:[{...goal,achieved:true,evidence:'How much is the rent?',answer_status:'confirmed'}],safety:false});
  }
  if(pathname.endsWith('/speech')){
    const body=request.postDataJSON();
    assert.deepEqual(Object.keys(body).sort(),['consent','response_id']);
    assert.equal(body.consent,true);
    assert.ok(['opening','checked-reply'].includes(body.response_id));
    return route.fulfill({status:200,contentType:'audio/wav',body:body.response_id==='opening'?openingAudio:replyAudio});
  }
  if(pathname.endsWith('/finish'))return json({goals:[goal],feedback:[],unanswered:[],phrases:[],note:'Practice complete.'});
  if(request.method()==='DELETE')return json({deleted:true});
  if(pathname.endsWith('/status'))return route.fulfill({status:404,contentType:'application/json',body:'{}'});
  throw Error('Unexpected API request: '+pathname);
});
try {
  await page.goto(origin,{waitUntil:'networkidle'});
  await page.getByRole('button',{name:'Build my mission'}).click();
  await page.getByRole('button',{name:/Action - start Take/}).click();
  const voice=page.getByRole('region',{name:'Voice rehearsal',exact:true});
  const start=voice.getByRole('button',{name:'Start voice rehearsal'});
  assert.equal(await voice.getByRole('combobox').count(),0);
  assert.equal(await start.isDisabled(),true);
  await voice.getByRole('checkbox').check();
  await start.click();
  await voice.getByText('Listening. Take your time.',{exact:true}).waitFor();
  assert.equal(await page.locator('#message').isDisabled(),true);
  await voice.getByText('Checking the reply against your sources…',{exact:true}).waitFor();
  assert.equal(turns.length,1);
  assert.deepEqual(turns[0],{text:'How much is the rent?'});
  assert.equal(requests.filter(request=>request.pathname.endsWith('/speech')).length,1);
  assert.equal(await page.locator('.message.assistant').count(),1);
  resolveTurn();
  await voice.getByText('Your partner is speaking.',{exact:true}).waitFor();
  assert.equal(await page.locator('.message').count(),3);
  assert.match(await page.locator('.message.assistant').last().innerText(),/850/);
  await page.getByText(/View source evidence/).click();
  assert.equal(await page.getByText('Monthly rent: 850 euros.',{exact:true}).isVisible(),true);
  assert.equal(await page.evaluate(()=>window.voiceTestTracks.every(track=>!track.enabled)),true);
  await page.screenshot({path:process.env.VOICE_TEST_SCREENSHOT||path.join(folder,'voice-rehearsal.png'),fullPage:true});
  await voice.getByRole('button',{name:'Interrupt & speak'}).click();
  await voice.getByText('Listening. Take your time.',{exact:true}).waitFor();
  await voice.getByRole('button',{name:'Mute microphone',exact:true}).click();
  await voice.getByText('Microphone muted.',{exact:true}).waitFor();
  assert.equal(await page.evaluate(()=>window.voiceTestTracks.every(track=>!track.enabled)),true);
  await voice.getByRole('button',{name:'Unmute microphone'}).click();
  await voice.getByText('Listening. Take your time.',{exact:true}).waitFor();
  await voice.getByRole('button',{name:'Stop voice mode'}).click();
  assert.equal(await page.evaluate(()=>window.voiceTestTracks.every(track=>track.readyState==='ended')),true);
  assert.equal(await page.locator('#message').isEnabled(),true);
  assert.equal(await page.getByRole('button',{name:'Record a voice message'}).count(),0);
  await page.getByLabel('Interface language').selectOption('de');
  await page.getByRole('button',{name:'Sprachprobe starten'}).waitFor();
  await page.getByLabel('Sprache der Oberfläche').selectOption('es');
  await page.getByRole('button',{name:'Iniciar ensayo por voz'}).waitFor();
  await page.getByLabel('Idioma de la interfaz').selectOption('en');
  await page.setViewportSize({width:390,height:844});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),true);
  await start.click();
  await voice.getByText('Your partner is speaking.',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Back to the plan',exact:true}).click();
  assert.equal(await page.evaluate(()=>window.voiceTestTracks.every(track=>track.readyState==='ended')),true);
  await page.getByRole('button',{name:/End & delete session/}).click();
  await page.getByText('Session deleted on the server.',{exact:false}).waitFor();
  assert.equal(turns.length,1);
  assert.deepEqual(errors,[]);
  console.log('PASS: actual browser capture/VAD → automatic transcript → validation gate → stored-reply audio; interrupt, mute, stop, navigation, deletion, EN/DE/ES and mobile layout. Provider responses were mocked.');
} finally {
  resolveTurn();
  await browser.close();
  assert.equal(path.dirname(path.resolve(folder)),path.resolve(tmpdir()));
  assert.ok(path.basename(folder).startsWith('rehearsal-voice-'));
  await rm(folder,{recursive:true,force:true});
}
