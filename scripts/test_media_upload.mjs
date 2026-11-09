import assert from 'node:assert/strict';
import {test} from 'node:test';
import {uploadMedia} from '../app/api-client.js';
import {microphoneError} from '../app/media-errors.js';

test('media uploads snapshot bytes and preserve filename, consent and language',async t=>{
 const selected=new File(['recorded bytes'],'speech.wav',{type:'audio/wav'});
 let calls=0;
 t.mock.method(globalThis,'fetch',async (url,options)=>{
  calls++;
  assert.equal(url,'/api/speech/transcribe');
  const sent=options.body.get('file');
  assert.notEqual(sent,selected);
  assert.equal(sent.name,'speech.wav');
  assert.equal(sent.type,'audio/wav');
  assert.equal(await sent.text(),'recorded bytes');
  assert.equal(options.body.get('consent'),'true');
  assert.equal(options.body.get('language'),'German');
  return Response.json({segments:[{start:0,end:1,text:'Hallo'}]});
 });
 assert.equal((await uploadMedia(selected,'German')).segments[0].text,'Hallo');
 assert.equal(calls,1);
});

test('unreadable and oversized files fail before contacting the server',async t=>{
 t.mock.method(globalThis,'fetch',()=>{throw Error('Must not send');});
 await assert.rejects(uploadMedia({size:1,arrayBuffer:async()=>{throw Error('stale handle');}},'English'),/media file could not be read/);
 await assert.rejects(uploadMedia({size:4*1024*1024+1},'English'),/Maximum media size/);
 assert.equal(fetch.mock.callCount(),0);
});

test('cancelling while reading a file never sends its bytes',async t=>{
 const abort=new AbortController();
 t.mock.method(globalThis,'fetch',()=>{throw Error('Must not send');});
 await assert.rejects(uploadMedia({size:1,arrayBuffer:async()=>{abort.abort();return new ArrayBuffer(1);}},'English',abort.signal),{name:'AbortError'});
 assert.equal(fetch.mock.callCount(),0);
});

test('a missing capture device has an actionable message in both microphone modes',()=>{
 assert.match(microphoneError({name:'NotFoundError',message:'Requested device not found'}),/No microphone was found/);
 assert.match(microphoneError({name:'DevicesNotFoundError'}),/upload a recording/);
 assert.match(microphoneError({name:'NotAllowedError'}),/permission was denied/);
});
