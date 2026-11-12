// Simulates a lost POST response after commit, not provider quality.
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {chromium}=require(require.resolve('playwright',{paths:[process.cwd(),process.cwd()+'/.runtime/browser']}));
const base=process.env.RECOVERY_TEST_URL||'http://127.0.0.1:3000';
assert.ok(['http://127.0.0.1:3000','https://the-rehearsal-lab.vercel.app'].includes(base));
const browser=await chromium.launch({headless:true,...(process.env.CHROME_PATH?{executablePath:process.env.CHROME_PATH}:{})});
try{
 const page=await browser.newPage();await page.clock.install();
 let committed=null,posts=0;
 const goals=[{id:'0',text:'Ask about monthly rent',achieved:true,answer_status:'confirmed',evidence:'What is the rent?',answer_evidence:'Monthly rent is 850 euros.',answer_sources:['1']}];
 const opening={id:'opening',role:'assistant',content:'What would you like to know?',sources:[]};
 const reply={id:'reply',role:'assistant',content:'The rent is 850 euros.',sources:[]};
 await page.route('**/api/**',async route=>{
  const req=route.request(),url=new URL(req.url()).pathname;let result;
  if(url==='/api/config')result={mode:'live',speech_enabled:false,feedback_enabled:false};
  else if(url==='/api/sessions')result={id:'recovery',name:'Sample'};
  else if(url.endsWith('/mission'))result={scenario:'interview',goals,safety:false};
  else if(url.endsWith('/start'))result={turns:[opening],goals,safety:false};
  else if(url.endsWith('/turn')){committed=req.postDataJSON();posts++;return;/* Intentionally never fulfil: client must release itself. */}
  else if(url.endsWith('/state'))result={phase:'chat',pending:false,turns:[opening,{role:'user',content:committed.text,sources:[]},reply],goals,safety:false,completed_request_ids:[committed.request_id]};
  else if(url.endsWith('/finish'))result={goals,feedback:[{quote:committed.text,suggestion:'',explanation:'A clear question.'}],unanswered:[],phrases:[],note:'Review.'};
  else if(url.endsWith('/status'))result={phase:'chat'};
  else if(req.method()==='DELETE')result={deleted:true};
  else throw Error(url);
  await route.fulfill({json:result});
 });
 await page.goto(base);await page.getByRole('button',{name:/zvoove/}).click();
 await page.getByRole('button',{name:'Build my mission'}).click();
 await page.getByRole('button',{name:/Action - start Take 01/}).click();
 await page.locator('#message').fill('What is the rent?');
 await page.getByRole('button',{name:'Send message',exact:true}).click();
 await page.waitForFunction(()=>document.querySelector('.rehearsal-loading'));
 await page.clock.fastForward(11000);
 await page.getByText('This is taking longer than usual. If it times out, your draft stays available and you can check the saved conversation.',{exact:true}).waitFor();
 await page.clock.fastForward(55000);
 await page.getByRole('button',{name:'Check rehearsal',exact:true}).waitFor();
 assert.equal(await page.locator('#message').inputValue(),'What is the rent?');
 assert.equal(await page.getByRole('button',{name:'Check rehearsal',exact:true}).isEnabled(),true);
 assert.equal(await page.locator('.rehearsal-loading').count(),0);
  if(process.env.AXE_SCRIPT_PATH){
   await page.addScriptTag({path:process.env.AXE_SCRIPT_PATH});
   for(const theme of ['light','dark']){
    await page.getByRole('combobox',{name:'Appearance',exact:true}).selectOption(theme);
    const violations=await page.evaluate(async()=>{const result=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}});return result.violations.map(v=>v.id);});
    assert.deepEqual(violations,[],theme+' recovery accessibility');
   }
  }
 await page.getByRole('button',{name:'Check rehearsal',exact:true}).click();
 await page.getByText('The rent is 850 euros.',{exact:true}).waitFor();
 assert.equal(await page.locator('.message.user').count(),1);
 assert.equal(posts,1,'Recovery must read state, not re-send the committed turn');
 assert.equal(await page.locator('#message').inputValue(),'');
 await page.getByRole('button',{name:/Cut - finish/}).click();
 await page.getByRole('heading',{name:'What you made happen'}).waitFor();
 console.log('Lost-response deadline, visible timer, preserved draft, recovery without duplicate POST and finish passed.');
}finally{await browser.close();}
