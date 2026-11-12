import test from 'node:test';
import assert from 'node:assert/strict';
import {sourceNotice,validatedMissionGoals,validatedMissionScenario} from '../app/mission-plan.mjs';
test('source labels preserve provenance and never assume a public-page import',()=>{
 assert.equal(sourceNotice('reviewed_pdf_ocr'),'Source: uploaded PDF; OCR text reviewed by you.');
 assert.match(sourceNotice('pasted_transcript'),/user-pasted transcript/);
 assert.equal(sourceNotice('public_page'),null);
 assert.equal(sourceNotice('unknown'),null);
});
test('plan accepts concrete goals and rejects missing or placeholder response data',()=>{
 const goals=[{id:'0',text:' Ask about monthly rent ',achieved:false}];
 assert.equal(validatedMissionGoals(goals)[0].text,'Ask about monthly rent');
 assert.equal(goals[0].text,' Ask about monthly rent ');
 for(const invalid of [null,[],[{id:'0',text:''}],[{id:'0',text:'Mission goal 1'}],[{id:'0',text:'Ask about rent'},{id:'0',text:'Ask about pets'}]])assert.throws(()=>validatedMissionGoals(invalid));
});

test('automatic scenario selection must resolve to a supported scene before rendering',()=>{
 for(const scenario of ['apartment','interview','course','difficult'])assert.equal(validatedMissionScenario(scenario),scenario);
 for(const scenario of [undefined,null,'auto','unknown',{},[]])assert.throws(()=>validatedMissionScenario(scenario));
});
