import assert from 'node:assert/strict';
import {test} from 'node:test';
import {VoiceSession} from '../app/voice-session.js';

const deferred=()=>{let resolve;const promise=new Promise(done=>{resolve=done;});return {promise,resolve};};
const flush=async()=>{for(let i=0;i<20;i++)await new Promise(resolve=>setImmediate(resolve));};

function fixture(t,options={}) {
  let now=0,poll=null,amplitude=0;
  const calls=[],errors=[],changes=[],transcripts=[],audios=[];
  const track={enabled:true,stopped:false,stop(){this.stopped=true;}};
  const stream={getTracks:()=>[track],getAudioTracks:()=>[track]};
  class Context {
    state='running';
    resume=async()=>{};
    close=async()=>{this.state='closed';};
    createMediaStreamSource=()=>({connect(){},disconnect(){}});
    createAnalyser=()=>({fftSize:2048,getFloatTimeDomainData:array=>array.fill(amplitude)});
  }
  class Recorder {
    static isTypeSupported=type=>type==='audio/webm';
    state='inactive';
    constructor(){options.onRecorder?.(this);}
    start(){this.state='recording';}
    stop(){
      this.state='inactive';
      this.ondataavailable?.({data:new Blob(['fake bounded audio'])});
      this.onstop?.();
    }
  }
  class Audio {
    constructor(url){this.url=url;audios.push(this);}
    async play(){if(options.playError)throw options.playError;this.played=true;}
    pause(){this.paused=true;}
    removeAttribute(){}
    load(){}
  }
  t.mock.method(globalThis.performance,'now',()=>now);
  t.mock.method(globalThis,'setInterval',callback=>{poll=callback;return 7;});
  t.mock.method(globalThis,'clearInterval',()=>{poll=null;});
  const globals={window:{AudioContext:Context,MediaRecorder:Recorder},MediaRecorder:Recorder,Audio,
    navigator:{mediaDevices:{getUserMedia:()=>options.microphone||Promise.resolve(stream)}},
    fetch:async(url,init)=>{
      calls.push({url,init});
      if(url.endsWith('/transcribe'))return options.transcription||Response.json({text:options.text||'How much is the rent?'});
      if(url.endsWith('/speech'))return options.playback||new Response(new Blob(['audio'],{type:'audio/mpeg'}));
      throw Error('Unexpected endpoint: '+url);
    }};
  for(const [name,value] of Object.entries(globals)){
    const original=Object.getOwnPropertyDescriptor(globalThis,name);
    Object.defineProperty(globalThis,name,{configurable:true,writable:true,value});
    t.after(()=>{if(original)Object.defineProperty(globalThis,name,original);else delete globalThis[name];});
  }
  const engine=new VoiceSession({sessionId:'fixture-session',language:'German',
    onTurn:async text=>{
      calls.push({turn:text});
      return options.turn?options.turn.promise:{turn:{id:'validated-reply'},safety:!!options.safety};
    },
    onTranscript:text=>transcripts.push(text),onChange:state=>changes.push(state),onError:error=>errors.push(error)
  });
  t.after(()=>engine.stop());
  function tick(ms,value=0){amplitude=value;for(let elapsed=0;elapsed<ms;elapsed+=50){now+=50;poll?.();}}
  return {engine,calls,errors,changes,transcripts,audios,track,stream,tick};
}

test('voice waits for evidence validation, speaks only the stored reply ID, then listens again',async t=>{
  const turn=deferred();
  const f=fixture(t,{turn});
  await f.engine.start();
  f.tick(400,0.04);f.tick(1900);
  await flush();
  assert.equal(f.engine.state,'thinking');
  assert.equal(f.track.enabled,false);
  assert.equal(f.audios.length,0);
  assert.equal(f.calls.filter(call=>call.turn).length,1);
  const upload=f.calls[0].init.body;
  assert.equal(upload.get('consent'),'true');
  assert.equal(upload.get('language'),'German');
  assert.ok(upload.get('file').size>0);
  turn.resolve({turn:{id:'server-checked-42'},safety:false});
  await flush();
  assert.equal(f.engine.state,'speaking');
  const request=f.calls.find(call=>call.url?.endsWith('/speech'));
  assert.deepEqual(JSON.parse(request.init.body),{response_id:'server-checked-42',consent:true});
  assert.equal(f.audios.length,1);
  f.audios[0].onended();
  assert.equal(f.engine.state,'listening');
  assert.equal(f.track.enabled,true);
  assert.equal(f.audios[0].paused,true);
});

test('silence and a short noise spike make no provider requests and idle stops the mic',async t=>{
  const f=fixture(t);
  await f.engine.start();
  f.tick(100,0.04);f.tick(30000);
  assert.equal(f.calls.length,0);
  assert.equal(f.engine.active,false);
  assert.equal(f.track.stopped,true);
  assert.match(f.errors[0],/No speech/);
});

test('muting discards an unsent recording; unmuting resumes and stop releases the mic',async t=>{
  const f=fixture(t);
  await f.engine.start();f.tick(400,0.04);
  f.engine.toggleMute();f.tick(4000);
  assert.equal(f.engine.state,'muted');
  assert.equal(f.track.enabled,false);
  assert.equal(f.calls.length,0);
  f.engine.toggleMute();
  assert.equal(f.engine.state,'listening');
  f.engine.stop();f.tick(4000,0.04);
  assert.equal(f.track.stopped,true);
  assert.equal(f.calls.length,0);
});

test('stopping during transcription ignores even a late successful response',async t=>{
  const transcription=deferred();
  const f=fixture(t,{transcription:transcription.promise});
  await f.engine.start();f.tick(400,0.04);f.tick(1900);
  const signal=f.calls[0].init.signal;
  f.engine.stop();
  transcription.resolve(Response.json({text:'This must never be submitted.'}));
  await flush();
  assert.equal(signal.aborted,true);
  assert.equal(f.transcripts.length,0);
  assert.equal(f.calls.filter(call=>call.turn).length,0);
  assert.equal(f.engine.active,false);
});

test('an already submitted turn completes once after stop without playback or mic restart',async t=>{
  const turn=deferred();
  const f=fixture(t,{turn});
  await f.engine.start();f.tick(400,0.04);f.tick(1900);await flush();
  assert.equal(f.engine.state,'thinking');
  f.engine.stop();turn.resolve({turn:{id:'committed'},safety:false});await flush();
  assert.equal(f.calls.filter(call=>call.turn).length,1);
  assert.equal(f.audios.length,0);
  assert.equal(f.engine.active,false);
  assert.equal(f.track.stopped,true);
});

test('interrupt cancels pending playback and cannot play a stale late response',async t=>{
  const playback=deferred();
  const f=fixture(t,{playback:playback.promise});
  const start=f.engine.start('opening');await flush();
  assert.equal(f.engine.state,'preparing');
  const signal=f.calls[0].init.signal;
  f.engine.interrupt();
  playback.resolve(new Response(new Blob(['late audio'])));await start;
  assert.equal(signal.aborted,true);
  assert.equal(f.engine.state,'listening');
  assert.equal(f.audios.length,0);
  assert.equal(f.errors.length,0);
});

test('interrupt stops current playback and opens the microphone',async t=>{
  const f=fixture(t);
  await f.engine.start('opening');
  assert.equal(f.engine.state,'speaking');
  f.engine.toggleMute();f.engine.interrupt();
  assert.equal(f.audios[0].paused,true);
  assert.equal(f.engine.state,'listening');
  assert.equal(f.engine.muted,false);
  assert.equal(f.track.enabled,true);
});

test('late microphone permission after stop releases the acquired stream',async t=>{
  const microphone=deferred();
  const f=fixture(t,{microphone:microphone.promise});
  const start=f.engine.start();await flush();f.engine.stop();
  microphone.resolve(f.stream);await start;
  assert.equal(f.track.stopped,true);
  assert.equal(f.engine.active,false);
  assert.equal(f.calls.length,0);
});

test('oversized transcript is preserved for editing and never silently truncated or submitted',async t=>{
  const text='a'.repeat(2001);
  const f=fixture(t,{text});
  await f.engine.start();f.tick(400,0.04);f.tick(1900);await flush();
  assert.equal(f.transcripts[0],text);
  assert.equal(f.calls.filter(call=>call.turn).length,0);
  assert.equal(f.engine.active,false);
  assert.match(f.errors[0],/too long/);
});

test('a safety-paused reply stops voice without requesting speech',async t=>{
  const f=fixture(t,{safety:true});
  await f.engine.start();f.tick(400,0.04);f.tick(1900);await flush();
  assert.equal(f.calls.filter(call=>call.turn).length,1);
  assert.equal(f.calls.filter(call=>call.url?.endsWith('/speech')).length,0);
  assert.equal(f.engine.active,false);
});

test('blocked autoplay stops the loop with an actionable error',async t=>{
  const f=fixture(t,{playError:new DOMException('Blocked','NotAllowedError')});
  await f.engine.start('opening');
  assert.equal(f.engine.active,false);
  assert.equal(f.track.stopped,true);
  assert.match(f.errors[0],/blocked automatic audio/);
});

test('a failed transcription is not retried and cannot create a learner turn',async t=>{
  const f=fixture(t,{transcription:Response.json({detail:'Provider unavailable'},{status:503})});
  await f.engine.start();f.tick(400,0.04);f.tick(1900);await flush();
  assert.equal(f.calls.length,1);
  assert.equal(f.engine.active,false);
  assert.equal(f.errors[0],'Provider unavailable');
});

test('separated short noise bursts do not accumulate into a speech turn',async t=>{
  const f=fixture(t);
  await f.engine.start();
  for(let i=0;i<12;i++){f.tick(100,0.04);f.tick(500);}
  assert.equal(f.engine.state,'listening');
  assert.equal(f.calls.length,0);
});

test('continuous speech is bounded by the recording deadline',async t=>{
  const f=fixture(t);
  await f.engine.start();f.tick(90500,0.04);await flush();
  assert.equal(f.calls.filter(call=>call.url?.endsWith('/transcribe')).length,1);
  assert.equal(f.calls.filter(call=>call.turn).length,1);
});

test('manual send ends detected speech without waiting for silence',async t=>{
  const f=fixture(t);
  await f.engine.start();f.tick(400,0.04);
  f.engine.submitRecording();await flush();
  assert.equal(f.calls.filter(call=>call.turn).length,1);
  assert.equal(f.engine.state,'speaking');
});

test('the default voice turn submits after a short 1.2-second pause',async t=>{
  const f=fixture(t);
  await f.engine.start();f.tick(400,0.04);f.tick(1100);await flush();
  assert.equal(f.calls.length,0);
  f.tick(100);await flush();
  assert.equal(f.calls.filter(call=>call.turn).length,1);
});

test('speech endpoint failure stops without regenerating the already stored reply',async t=>{
  const f=fixture(t,{playback:Response.json({detail:'Daily allowance reached'},{status:429})});
  await f.engine.start();f.tick(400,0.04);f.tick(1900);await flush();
  assert.equal(f.calls.filter(call=>call.turn).length,1);
  assert.equal(f.calls.filter(call=>call.url?.endsWith('/speech')).length,1);
  assert.equal(f.engine.active,false);
  assert.equal(f.errors[0],'Daily allowance reached');
});
