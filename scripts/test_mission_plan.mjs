import test from 'node:test';
import assert from 'node:assert/strict';
import {sourceNotice,validatedMissionGoals} from '../app/mission-plan.mjs';
test('source labels preserve provenance and never assume a public-page import',()=>{
 assert.equal(sourceNotice('reviewed_pdf_ocr'),'Source: uploaded PDF; OCR text reviewed by you.');
 assert.match(sourceNotice('pasted_transcript'),/user-pasted transcript/);
 assert.match(sourceNotice('public_page'),/public-page snapshot/);
 assert.equal(sourceNotice('unknown'),null);
});
test('plan accepts concrete goals and rejects missing or placeholder response data',()=>{
 const goals=[{id:'0',text:' Ask about monthly rent ',achieved:false}];
 assert.equal(validatedMissionGoals(goals)[0].text,'Ask about monthly rent');
 assert.equal(goals[0].text,' Ask about monthly rent ');
 for(const invalid of [null,[],[{id:'0',text:''}],[{id:'0',text:'Mission goal 1'}],[{id:'0',text:'Ask about rent'},{id:'0',text:'Ask about pets'}]])assert.throws(()=>validatedMissionGoals(invalid));
});
