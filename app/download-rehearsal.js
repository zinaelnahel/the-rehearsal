// Explicit browser-only export. No network request or browser storage.
export function downloadRehearsal({scenario,language,mode,take,turns,debrief}) {
 const lines=[
  'The Rehearsal — conversation & review',
  `${scenario} | ${language} | Take ${String(take).padStart(2,'0')}`,
  mode==='demo'?'Scripted demo conversation':'AI role-play conversation',
  'Practice only. Partner replies are not promises from the real person.',
  '', 'CONVERSATION', ''
 ];
 for(const turn of turns) {
  lines.push(turn.safety?'SUPPORT NOTE':turn.role==='user'?'YOU':'PARTNER',turn.content,'');
 }
 if(debrief) {
  lines.push('REVIEW',debrief.note,'','GOALS');
  for(const goal of debrief.goals) lines.push(`- ${goal.text} — ${goal.achieved?'practised':'not yet practised'}; answer: ${goal.answer_status.replaceAll('_',' ')}`);
  if(debrief.feedback.length) {
   lines.push('','COMMUNICATION NOTES');
   for(const note of debrief.feedback) lines.push(`You said: ${note.quote}`,note.suggestion?`Suggestion: ${note.suggestion}`:'',note.explanation,'');
  }
  if(debrief.unanswered.length) lines.push('','OPEN QUESTIONS',...debrief.unanswered.map(q=>`- ${q}`));
  if(debrief.phrases.length) lines.push('','PHRASES TO KEEP',...debrief.phrases.map(p=>`- ${p}`));
 }
 lines.push('','Downloaded at your request. This file stays on your device after you delete the app session.','Independent project. No affiliation or endorsement.');
 const url=URL.createObjectURL(new Blob(['\uFEFF'+lines.join('\n')],{type:'text/plain;charset=utf-8'}));
 const anchor=document.createElement('a');
 anchor.href=url;anchor.download=`the-rehearsal-take-${String(take).padStart(2,'0')}.txt`;
 document.body.appendChild(anchor);anchor.click();anchor.remove();
 setTimeout(()=>URL.revokeObjectURL(url),1000);
}
