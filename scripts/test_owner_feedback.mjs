import assert from 'node:assert/strict';
import {test} from 'node:test';
import {authorised,renderReport} from '../app/owner/feedback/report.mjs';
const secret='s'.repeat(40);
test('owner authentication fails closed and checks both username and password',()=>{
 const basic=value=>'Basic '+Buffer.from(value).toString('base64');
 assert.equal(authorised(basic('owner:'+secret),secret),true);
 for(const header of [null,'Bearer '+secret,basic('someone:'+secret),basic('owner:wrong'),'Basic broken'])assert.equal(authorised(header,secret),false);
 assert.equal(authorised(basic('owner:short'),'short'),false);
});
test('report escapes metadata and offers downloads without putting credentials in HTML',()=>{
 const summary={ratings:1,useful:1,unhelpful:0,useful_percent:100,mean_turn_latency_ms:3000};
 const data={days:30,retention_days:90,dialogue_ratings:summary,all_ratings:summary,response_ratings:{ratings:0},negative_reasons:{'<script>':1},breakdowns:{language:{'<img src=x>':summary}},quality_ratings:Object.fromEntries(['relevance','memory','continuity','role_consistency','grounding','language_agreement'].map(key=>[key,{pass:1,fail:0,uncertain:0,unrated:0}]))};
 const html=renderReport(data);
 assert.ok(html.includes('Download JSON'));assert.ok(html.includes('Download HTML'));
 assert.ok(html.includes('temporary filesystem'));assert.ok(html.includes('restorable database backup'));
 assert.ok(html.includes('&lt;script&gt;'));assert.ok(html.includes('&lt;img src=x&gt;'));
 assert.ok(!html.includes(secret));assert.ok(!html.includes('<script>'));
 assert.ok(!renderReport(data,true).includes('Download JSON'));
});
test('owner route challenges before fetching and sends credentials only to the backend',async t=>{
 const {GET}=await import('../app/owner/feedback/route.js');
 const previous=Object.fromEntries(['FEEDBACK_OWNER_TOKEN','BACKEND_URL','API_PROXY_TOKEN'].map(key=>[key,process.env[key]]));
 Object.assign(process.env,{FEEDBACK_OWNER_TOKEN:secret,BACKEND_URL:'http://127.0.0.1:8000',API_PROXY_TOKEN:'test-proxy'});
 t.after(()=>{for(const [key,value] of Object.entries(previous))if(value===undefined)delete process.env[key];else process.env[key]=value;});
 const fetch=t.mock.method(globalThis,'fetch',async(url,options)=>{
  assert.equal(url,'http://127.0.0.1:8000/api/owner/feedback?days=7');
  assert.equal(options.headers['x-feedback-owner-token'],secret);
  assert.equal(options.headers['x-rehearsal-token'],'test-proxy');
  assert.equal(options.headers.authorization,undefined);
  return Response.json({all_ratings:{ratings:0}});
 });
 const locked=await GET(new Request('https://example.test/owner/feedback'));
 assert.equal(locked.status,401);assert.ok(locked.headers.get('www-authenticate').startsWith('Basic '));
 assert.equal(fetch.mock.callCount(),0);
 const headers={authorization:'Basic '+Buffer.from('owner:'+secret).toString('base64')};
 const report=await GET(new Request('https://example.test/owner/feedback?days=7&download=json',{headers}));
 assert.equal(report.status,200);assert.equal(report.headers.get('cache-control'),'private, no-store, max-age=0');
 assert.match(report.headers.get('content-disposition'),/attachment; filename="rehearsal-feedback-7-days.json"/);
 assert.deepEqual(await report.json(),{all_ratings:{ratings:0}});
 assert.equal((await GET(new Request('https://example.test/owner/feedback?days=999',{headers}))).status,400);
 assert.equal(fetch.mock.callCount(),1);
});
