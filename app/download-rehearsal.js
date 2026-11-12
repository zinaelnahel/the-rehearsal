import {jsPDF} from 'jspdf';

// Generated entirely on the device; conversation content stays in the browser.
export function createRehearsalPdf({scenario,language,mode,take,turns,debrief}) {
 const pdf=new jsPDF({unit:'pt',format:'letter',compress:true});
 const bottom=720,lineHeight=14;
 let y=72;
 pdf.setProperties({title:`The Rehearsal - ${scenario} - Take ${take}`,author:'The Rehearsal',subject:'Conversation screenplay and rehearsal notes'});
 const clean=value=>String(value??'').replace(/\r\n?/g,'\n').replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/g,'').replace(/\u202f|\u00a0/g,' ').replace(/\u2192|\u21b3/g,'>');
 const font=(bold=false,size=12)=>{pdf.setFont('courier',bold?'bold':'normal');pdf.setFontSize(size);pdf.setTextColor(30);};
 const newPage=()=>{pdf.addPage();y=72;};
 const space=height=>{if(y+height>bottom)newPage();};
 function paragraph(text,{x=108,w=432,bold=false,size=12,gap=14}={}) {
  font(bold,size);
  for(const line of pdf.splitTextToSize(clean(text),w)){space(lineHeight);pdf.text(line,x,y);y+=lineHeight;}
  y+=gap;
 }
 function heading(text){space(56);paragraph(text.toUpperCase(),{bold:true,gap:18});}
 function centered(text,at,size=12,bold=false){font(bold,size);const lines=pdf.splitTextToSize(clean(text),432);pdf.text(lines,306,at,{align:'center',lineHeightFactor:1.3});return at+lines.length*size*1.3;}
 centered('THE REHEARSAL',238,24,true);
 const titleEnd=centered(scenario,284,16,true);
 centered(`TAKE ${String(take).padStart(2,'0')}  /  ${language}`,Math.max(346,titleEnd+28));
 centered(mode==='demo'?'A scripted practice scene':'A conversation in rehearsal',390);
 centered('Conversation & rehearsal notes',414,10);
 y=624;
 paragraph('Practice only. Partner replies are not promises from the real person.',{size:10,w:396});
 paragraph('Independent project. No affiliation or endorsement.',{size:9});
 newPage();heading('INT. THE REHEARSAL - PRACTICE SESSION');
 for(const turn of turns) {
  const speaker=turn.safety?'SUPPORT NOTE':turn.role==='user'?'YOU':'PARTNER';
  font();const lines=pdf.splitTextToSize(clean(turn.content),252);
  space(14+Math.min(lines.length,3)*lineHeight+14);
  paragraph(speaker,{x:252,w:288,bold:true,gap:0});
  for(const line of lines) {
   if(y+lineHeight>bottom){newPage();paragraph(`${speaker} (CONT'D)`,{x:252,w:288,bold:true,gap:0});}
   font();pdf.text(line,180,y);y+=lineHeight;
  }
  y+=14;
 }
 space(28);paragraph('END OF SCENE',{bold:true});
 if(debrief) {
  newPage();heading('REHEARSAL NOTES');paragraph(debrief.note);
  if(debrief.goals?.length){heading('Your mission');for(const goal of debrief.goals){space(56);paragraph(goal.text,{bold:true,gap:4});paragraph(`${goal.achieved?'Practised':'Not yet practised'} / Answer: ${(goal.answer_status||'unknown').replaceAll('_',' ')}`,{size:10});}}
  if(debrief.feedback?.length){heading('Communication notes');for(const note of debrief.feedback){space(70);paragraph(`You said: ${note.quote}`,{gap:6});if(note.suggestion)paragraph(`Try: ${note.suggestion}`,{bold:true,gap:6});paragraph(note.explanation);}}
  if(debrief.unanswered?.length){heading('Open questions');for(const question of debrief.unanswered)paragraph(question);}
  if(debrief.phrases?.length){heading('Phrases to keep');for(const phrase of debrief.phrases)paragraph(phrase,{bold:true});}
  space(70);paragraph('Downloaded at your request. This copy stays on your device after you delete the app session.',{size:9});
 }
 const pages=pdf.getNumberOfPages();
 for(let page=2;page<=pages;page++) {
  pdf.setPage(page);font(false,9);pdf.setTextColor(115);
  pdf.text('THE REHEARSAL',108,44);pdf.text(`${page-1}.`,540,44,{align:'right'});
  pdf.setDrawColor(210);pdf.setLineWidth(0.4);pdf.line(108,752,540,752);
  pdf.text(`TAKE ${String(take).padStart(2,'0')}  /  ${page-1} OF ${pages-1}`,108,768);
 }
 return pdf;
}

export function downloadRehearsal(rehearsal) {
 createRehearsalPdf(rehearsal).save(`the-rehearsal-take-${String(rehearsal.take).padStart(2,'0')}.pdf`);
}
