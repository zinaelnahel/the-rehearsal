import assert from 'node:assert/strict';
import {readFileSync,writeFileSync} from 'node:fs';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {chromium}=require(require.resolve('playwright',{paths:[process.cwd(),process.cwd()+'/.runtime/browser']}));
const base=process.env.A11Y_TEST_URL||'http://127.0.0.1:3000';
assert.ok(['http://127.0.0.1:3000','https://the-rehearsal-lab.vercel.app'].includes(base));
const report={base,scans:[],errors:[]};
const browser=await chromium.launch({headless:true,...(process.env.CHROME_PATH?{executablePath:process.env.CHROME_PATH}:{})});
const goals=[{id:'0',text:'Decline the weekend request clearly',achieved:true,evidence:'No puedo este fin de semana.',answer_status:'not_applicable'},
 {id:'1',text:'Set a boundary about your time',achieved:true,evidence:'Pregúntame antes.',answer_status:'not_applicable'},
 {id:'2',text:'Reaffirm the boundary after pushback',achieved:true,evidence:'Mi respuesta sigue siendo no.',answer_status:'not_applicable'}];
const source={id:'1',source:'Voice message',location:'0.00s–6.65s',text:'Hola. He organizado la mudanza para este sábado, de diez a una.',url:'/api/samples/difficult/audio',start:0,end:6.65};
async function scan(page,name){
 await page.addScriptTag({path:process.env.AXE_SCRIPT_PATH||require.resolve('axe-core/axe.min.js',{paths:[process.cwd(),process.cwd()+'/.runtime/browser']})});
 const data=await page.evaluate(()=>axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa','best-practice']}}));
 const violations=data.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary,html:n.html}))}));
 report.scans.push({name,violations,incomplete:data.incomplete.map(v=>({id:v.id,count:v.nodes.length,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary,html:n.html}))}))});
 const viewport=page.viewportSize();
 await page.setViewportSize({width:320,height:900});
 const spacing=await page.addStyleTag({content:'p{margin-bottom:2em!important}*{line-height:1.5!important;letter-spacing:.12em!important;word-spacing:.16em!important}'});
 const overflow=await page.evaluate(()=>[...document.querySelectorAll('body *')].filter(n=>n.getBoundingClientRect().right>innerWidth+1&&getComputedStyle(n).position!=='absolute').map(n=>({tag:n.tagName,class:n.className,right:n.getBoundingClientRect().right})).slice(-20));
 if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1))console.log('OVERFLOW',JSON.stringify(overflow));
 assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),name+' must reflow at 320px with increased text spacing');
 await spacing.evaluate(node=>node.remove());await page.setViewportSize(viewport);
 console.log(name,violations.map(v=>v.id).join(',')||'PASS');
}
try{
 for(const theme of ['light','dark']){
  const context=await browser.newContext({viewport:{width:1280,height:1000},colorScheme:theme});
  await context.route('**/api/**',async route=>{
   const req=route.request(),url=new URL(req.url()).pathname;
   if(url==='/api/samples/difficult/audio')return route.fulfill({contentType:'audio/wav',body:readFileSync('samples/audio/family-boundary.es.wav')});
   const reply={id:'reply',role:'assistant',content:'Entiendo tu decisión. [1]',sources:[source]};
   let result;
   if(url==='/api/config')result={mode:'live',speech_enabled:true,feedback_enabled:true,vector_store:'memory'};
   else if(url==='/api/sessions')result={id:'a11y',name:'Sample source'};
   else if(url==='/api/upload')result={id:'ocr',name:'scan.pdf',requires_confirmation:true,source_method:'pdf_ocr',pages:[{location:'Page 1',text:'Rent is 900 euros.',ocr:true}]};
   else if(url.endsWith('/mission'))result={scenario:'difficult',goals,safety:false};
   else if(url.endsWith('/start'))result={turns:[reply],goals,safety:false};
   else if(url.endsWith('/turn'))result={turn:reply,goals,safety:false};
   else if(url.endsWith('/finish'))result={goals,feedback:[{quote:'No puedo este fin de semana.',suggestion:'',explanation:'You clearly stated your availability.'}],unanswered:[],phrases:['No puedo este fin de semana.'],note:'Review.',feedback_id:'review'};
   else if(url.endsWith('/source/1'))result={kind:'transcript',focus:source,sections:[{location:source.location,text:source.text,selected:true}],original_audio_url:'/api/samples/difficult/audio',audio_timed:true};
   else if(url.endsWith('/status'))result={phase:'chat'};
   else if(req.method()==='DELETE')result={deleted:true};
   else throw Error('Unexpected mocked API '+url);
   return route.fulfill({json:result});
  });
  const page=await context.newPage();page.on('pageerror',e=>report.errors.push(e.message));
  await page.goto(base);await page.getByRole('button',{name:'Build my mission'}).waitFor();
  await page.keyboard.press('Tab');assert.equal(await page.evaluate(()=>document.activeElement.className),'skip-link');
  await page.getByRole('combobox',{name:'Appearance',exact:true}).selectOption(theme);
  await scan(page,theme+'-setup');
  await page.getByRole('tab',{name:'Try a sample',exact:true}).focus();
  await page.keyboard.press('ArrowRight');
  assert.equal(await page.getByRole('tab',{name:'Your situation',exact:true}).getAttribute('aria-selected'),'true');
  assert.equal(await page.evaluate(()=>document.activeElement.id),'source-tab-situation');
  await page.keyboard.press('End');assert.equal(await page.evaluate(()=>document.activeElement.id),'source-tab-media');
  await page.keyboard.press('Home');assert.equal(await page.evaluate(()=>document.activeElement.id),'source-tab-sample');
  await page.keyboard.press('Tab');
  await page.locator('.skip-link').focus();await page.keyboard.press('Enter');
  assert.equal(await page.evaluate(()=>document.activeElement.id),'main-content');
  await page.locator('.library-panel').evaluate(node=>node.open=true);
  await scan(page,theme+'-library');
  await page.getByRole('button',{name:/A difficult conversation/}).click();
  await page.getByRole('checkbox',{name:'I reviewed this audio transcript and want to use it for my rehearsal.'}).check();
  await scan(page,theme+'-audio');
  await page.getByRole('button',{name:'Build my mission'}).click();
  await page.getByRole('heading',{name:'Your conversation checklist'}).waitFor();
  await scan(page,theme+'-plan');
  await page.getByRole('button',{name:/Action - start Take 01/}).click();
  await page.locator('#message').waitFor();
  await page.getByText('Need a little help?',{exact:true}).click();
  await page.getByText('Rehearse out loud',{exact:true}).click();
  await scan(page,theme+'-chat');
  await page.locator('.messages details').first().evaluate(n=>n.open=true);
  await page.getByRole('button',{name:/Play audio excerpt/}).click();
  await page.getByRole('dialog').waitFor();await page.getByText('The highlighted passage is the evidence used for this reply.').waitFor();
  await scan(page,theme+'-source-dialog');
  await page.keyboard.press('Escape');assert.equal(await page.getByRole('dialog').count(),0);
  assert.match(await page.evaluate(()=>document.activeElement.textContent),/Play audio excerpt/);
  await page.getByRole('button',{name:/Cut - finish/}).click();
  await page.getByRole('heading',{name:'What you made happen'}).waitFor();
  await scan(page,theme+'-review');
  await page.screenshot({path:'.runtime/a11y-'+theme+'-review.png',fullPage:true});
  await page.goto(base);await page.getByRole('button',{name:'Build my mission'}).waitFor();
  assert.equal(await page.locator('html').getAttribute('data-theme'),theme);
  await page.getByRole('tab',{name:'Audio / video',exact:true}).click();
  await scan(page,theme+'-video-import');
  await page.locator('#media-source-kind').selectOption('upload');
  await scan(page,theme+'-audio-upload');
  await page.getByRole('tab',{name:'Your situation',exact:true}).click();
  await page.locator('#situation-source-kind').selectOption('file');
  await page.locator('#upload').setInputFiles({name:'scan.pdf',mimeType:'application/pdf',buffer:Buffer.from('%PDF-fixture')});
  await page.getByRole('button',{name:'Build my mission'}).click();
  await page.getByRole('dialog').waitFor();
  await scan(page,theme+'-ocr-dialog');
  await page.keyboard.press('Escape');
  await page.goto(base);await page.getByRole('button',{name:'Build my mission'}).waitFor();
  await page.getByRole('combobox',{name:'Appearance',exact:true}).selectOption('system');
  const opposite=theme==='dark'?'light':'dark';await page.emulateMedia({colorScheme:opposite});
  await page.waitForFunction(expected=>document.documentElement.dataset.theme===expected,opposite);
  await page.getByRole('combobox',{name:'Appearance',exact:true}).selectOption(theme);
  await page.setViewportSize({width:390,height:844});
  for(const locale of ['en','de','es']){
   await page.locator('.interface-language select').selectOption(locale);
   await scan(page,theme+'-mobile-'+locale);
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  }
  await page.screenshot({path:'.runtime/a11y-'+theme+'-mobile.png',fullPage:true});
  await context.close();
 }
}finally{await browser.close();writeFileSync('.runtime/accessibility-audit.json',JSON.stringify(report,null,2));}
assert.deepEqual(report.errors,[]);
assert.equal(report.scans.filter(s=>s.violations.length).length,0,'Accessibility violations remain; see .runtime/accessibility-audit.json');
assert.ok(report.scans.every(s=>s.incomplete.every(rule=>rule.id==='color-contrast'&&rule.nodes.every(node=>node.summary.includes('only non-text characters')))),
 'An accessibility rule requires further review; inspect the report before claiming the audit passed.');
