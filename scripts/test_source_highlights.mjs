import test from 'node:test';
import assert from 'node:assert/strict';
import {highlightRanges} from '../app/source-highlights.mjs';

test('only supporting bullets are highlighted inside full page context',()=>{
 const passage='Your benefits\n- Pension scheme\n- Staff discounts\nUnrelated context';
 const text='Page heading\n'+passage+'\nPage footer';
 const ranges=highlightRanges(text,passage,['- Pension scheme','- Staff discounts']);
 assert.deepEqual(ranges.map(([start,end])=>text.slice(start,end)),['- Pension scheme','- Staff discounts']);
});
test('missing or fabricated excerpts never highlight the entire passage',()=>{
 assert.deepEqual(highlightRanges('Salary unknown','Salary unknown',[]),[]);
 assert.deepEqual(highlightRanges('Salary unknown','Salary unknown',['EUR 90,000']),[]);
});
test('duplicate and overlapping excerpts merge without marking extra text',()=>{
 assert.deepEqual(highlightRanges('abc def ghi','abc def ghi',['abc def','def ghi','abc def']),[[0,11]]);
});
test('repeated text elsewhere on the page is not highlighted',()=>{
 const text='Pension scheme\nBenefits: Pension scheme';
 assert.deepEqual(highlightRanges(text,'Benefits: Pension scheme',['Pension scheme']),[[25,39]]);
});
