'use client';
import {useState} from 'react';

const branches=[
 {id:'clear',label:'They give a clear answer',icon:'✓',next:'Check the evidence. Confirm what you understood.',ending:'Ask your next useful question.'},
 {id:'unknown',label:'The detail is missing',icon:'?',next:'Ask who can confirm it, or how to follow up.',ending:'Keep the question open for real life.'},
 {id:'different',label:'They ask you something back',icon:'↩',next:'Explain your priorities. Then return to your question.',ending:'Agree on a practical next step.'}
];

export default function DialogueMap({goals,compact=false}) {
 const [selected,setSelected]=useState(null);
 const [branch,setBranch]=useState('clear');
 const goal=goals.find(g=>g.id===selected)||goals[0];
 const active=branches.find(b=>b.id===branch);
 if(!goal)return null;
 return <section className={'dialogue-map '+(compact?'map-compact':'')} aria-label="Possible dialogue flow">
  <div className="map-heading"><div><div className="eyebrow">THE PLAN / POSSIBLE PATHS</div><h2>A plan for the unplanned.</h2></div><span className="map-take">TAKE 01 ↗</span></div>
  <p className="map-caption">A rehearsal sketch, not a prediction. No branch adds facts to your document.</p>
  <div className="map-goals" aria-label="Choose a goal to map">{goals.map((g,i)=><button key={g.id} type="button" aria-pressed={g.id===goal.id} onClick={()=>setSelected(g.id)}>Goal {i+1}{g.achieved?' · practised':''}</button>)}</div>
  <div className="flow-root"><span>YOUR OPENING INTENT</span><strong>{goal.text}</strong>{goal.answer_status==='unknown'&&<small>Current answer: still unknown</small>}</div>
  <div className="flow-connectors" aria-hidden="true"><svg viewBox="0 0 600 45" preserveAspectRatio="none"><path d="M300 0 V18 M100 40 V18 H500 V40 M300 18 V40"/><path d="M95 35 L100 40 L105 35 M295 35 L300 40 L305 35 M495 35 L500 40 L505 35"/></svg></div>
  <div className="flow-branches">{branches.map(b=><button key={b.id} type="button" aria-pressed={branch===b.id} className={branch===b.id?'chosen':''} onClick={()=>setBranch(b.id)}><span>{b.icon}</span>{b.label}</button>)}</div>
  <div className="flow-next-connector" aria-hidden="true">↓</div>
  <div className="flow-next" role="status"><span>YOUR NEXT MOVE</span><strong>{active.next}</strong><p>{active.ending}</p></div>
  <p className="map-footnote">People can surprise you. You can pause, ask for help, or try another path.</p>
 </section>;
}
