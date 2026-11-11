import assert from 'node:assert/strict';
import {test} from 'node:test';
import {api} from '../app/api-client.js';

for(const stage of ['headers','body'])test('hard deadline releases a request stuck at '+stage,async t=>{
 t.mock.timers.enable({apis:['setTimeout']});
 t.mock.method(globalThis,'fetch',async()=>stage==='headers'?new Promise(()=>{}):{ok:true,text:()=>new Promise(()=>{})});
 const request=api('/sessions/demo/turn',{text:'Question'});
 const checked=assert.rejects(request,/draft is kept/);
 await Promise.resolve();t.mock.timers.tick(65001);await checked;
 assert.equal(fetch.mock.callCount(),1,'Failed POSTs must never be retried automatically');
});
