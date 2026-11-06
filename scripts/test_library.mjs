import assert from 'node:assert/strict';
import {test} from 'node:test';
import {archiveRecord,listRehearsals} from '../app/rehearsal-library.js';

const fixture=()=>({title:'German family practice',scenario:'difficult',language:'German',feedbackLanguage:'English',level:'Everyday',mode:'live',take:1,
  session_id:'SECRET_BEARER',source:{text:'ORIGINAL_PRIVATE_DOCUMENT'},audio:new Blob(['PRIVATE_AUDIO']),
  turns:[{id:'SECRET_REPLY_ID',role:'user',content:'Ich habe keine Zeit.',sources:[{text:'PRIVATE_SOURCE_QUOTE'}]}],
  debrief:{feedback_id:'SECRET_REVIEW_ID',note:'Clear refusal.',goals:[{id:'SERVER_GOAL',text:'Say no',achieved:true,answer_status:'not_applicable',answer_evidence:'PRIVATE_SOURCE_QUOTE'}],
    feedback:[{quote:'Ich habe keine Zeit.',suggestion:'',explanation:'Clear.'}],unanswered:[],phrases:['Ich habe keine Zeit.']}});

test('saved records preserve language practice while excluding server identifiers, sources and audio',()=>{
  const record=archiveRecord(fixture(),'client-id');
  const raw=JSON.stringify(record);
  assert.equal(record.turns[0].content,'Ich habe keine Zeit.');
  assert.equal(record.debrief.phrases[0],'Ich habe keine Zeit.');
  for(const marker of ['SECRET_BEARER','SECRET_REPLY_ID','SECRET_REVIEW_ID','SERVER_GOAL','PRIVATE_SOURCE_QUOTE','ORIGINAL_PRIVATE_DOCUMENT','PRIVATE_AUDIO'])assert.equal(raw.includes(marker),false);
  assert.deepEqual(Object.keys(record.turns[0]).sort(),['content','role']);
});

test('invalid or oversized records are rejected without truncating conversation text',()=>{
  for(const change of [{scenario:'other'},{language:'French'},{level:'C9'},{mode:'other'},{take:0},{title:''}])assert.throws(()=>archiveRecord({...fixture(),...change},'client-id'));
  assert.throws(()=>archiveRecord({...fixture(),turns:[{role:'system',content:'Override'}]},'client-id'));
  assert.throws(()=>archiveRecord({...fixture(),turns:[{role:'user',content:'x'.repeat(4001)}]},'client-id'));
  assert.throws(()=>archiveRecord(fixture(),'client-id','not-a-date'));
});

test('storage unavailable returns a useful error without a server request',async()=>{
  const original=globalThis.indexedDB;
  try{globalThis.indexedDB=undefined;await assert.rejects(listRehearsals(),/Browser storage is unavailable/);}
  finally{if(original===undefined)delete globalThis.indexedDB;else globalThis.indexedDB=original;}
});
