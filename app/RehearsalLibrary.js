'use client';
import {useEffect,useRef,useState} from 'react';
import {useI18n} from './i18n';
import {listRehearsals,saveRehearsal,deleteRehearsal,clearRehearsals} from './rehearsal-library';
import {downloadRehearsal} from './download-rehearsal';

const labels={apartment:'Apartment viewing',interview:'Job interview',course:'Course enquiry',difficult:'A difficult conversation'};
const codes={English:'en',German:'de',Spanish:'es'};

function SavedTake({record,onDelete}) {
  const {t,locale}=useI18n();
  return <article className="saved-take">
    <h3>{record.title}</h3><p>{t(labels[record.scenario])} · {t(record.language)} · {t(record.level)} · {t('Take')} {record.take}<br/>
      <time dateTime={record.createdAt}>{new Date(record.createdAt).toLocaleString(locale)}</time></p>
    <p className="subtle">{record.mode==='demo'?t('Saved scripted practice'):t('Saved AI practice')} · {t('Feedback in')} {t(record.feedbackLanguage)}<br/>{t('Historical practice, not a current confirmation of source facts.')}</p>
    <p>{record.debrief.goals.filter(goal=>goal.achieved).length} / {record.debrief.goals.length} {t('learner actions practised')}</p>
    <details open><summary>{t('Saved conversation')}</summary><div className="saved-conversation">{record.turns.map((turn,index)=><div key={index} className={'saved-turn '+turn.role}><strong>{turn.role==='user'?t('YOU'):t('YOUR PARTNER')}</strong><p lang={codes[record.language]}>{turn.content}</p></div>)}</div></details>
    <h4>{t('Notes on your actual turns')}</h4><p>{record.debrief.note}</p>
    {record.debrief.feedback.map((note,index)=><div className="feedback-item" key={index}><blockquote lang={codes[record.language]}>{note.quote}</blockquote>{note.suggestion&&<p lang={codes[record.language]}>{note.suggestion}</p>}<p>{note.explanation}</p></div>)}
    <h4>{t('Your conversation checklist')}</h4><ul>{record.debrief.goals.map((goal,index)=><li key={index}>{goal.text} · {goal.achieved?t('Yes'):t('Not yet')}</li>)}</ul>
    <h4>{t('A few words to bring along')}</h4>{record.debrief.phrases.map((phrase,index)=><p className="phrase" lang={codes[record.language]} key={index}>{phrase}</p>)}
    {!!record.debrief.unanswered.length&&<><h4>{t('Keep these questions open')}</h4><ul>{record.debrief.unanswered.map((question,index)=><li key={index}>{question}</li>)}</ul></>}
    <div className="library-actions"><button className="secondary" type="button" onClick={()=>downloadRehearsal({...record,scenario:t(labels[record.scenario])})}>{t('Download screenplay (.pdf)')}</button><button className="text-button" type="button" onClick={()=>onDelete(record)}>{t('Delete saved rehearsal')}</button></div>
  </article>;
}

export default function RehearsalLibrary({current,currentKey}) {
  const {t,errorText}=useI18n();
  const [records,setRecords]=useState([]),[loading,setLoading]=useState(true),[pending,setPending]=useState(false);
  const [error,setError]=useState(''),[notice,setNotice]=useState(''),[unreadable,setUnreadable]=useState(0);
  const [title,setTitle]=useState(''),[consent,setConsent]=useState(false),[selected,setSelected]=useState(''),[compare,setCompare]=useState(''),[filter,setFilter]=useState('');
  const keys=useRef(new Map()),library=useRef(null),mounted=useRef(true),working=useRef(false);
  async function refresh(){const result=await listRehearsals();if(mounted.current){setRecords(result.records);setUnreadable(result.unreadable);}}
  useEffect(()=>{
    mounted.current=true;
    const load=()=>refresh().catch(()=>{if(mounted.current)setError('Browser storage is unavailable. You can download the rehearsal instead.');});
    void load().finally(()=>{if(mounted.current)setLoading(false);});
    const visible=()=>{if(!document.hidden)void load();};
    window.addEventListener('focus',load);document.addEventListener('visibilitychange',visible);
    return()=>{mounted.current=false;window.removeEventListener('focus',load);document.removeEventListener('visibilitychange',visible);};
  },[]);
  useEffect(()=>{const saved=records.find(record=>record.id===keys.current.get(currentKey));setTitle(saved?.title||(current?t(labels[current.scenario]):''));setConsent(false);setNotice('');},[currentKey]);
  async function work(action){if(working.current)return;working.current=true;setPending(true);setError('');try{await action();}catch(error){setError(error.message);}finally{working.current=false;if(mounted.current)setPending(false);}}
  async function save(){await work(async()=>{
    if(!current||!consent)return;
    if(!keys.current.has(currentKey))keys.current.set(currentKey,crypto.randomUUID());
    const record=await saveRehearsal({...current,title},keys.current.get(currentKey));
    await refresh();setSelected(record.id);setCompare('');setNotice('Saved on this device. You can revisit it in your rehearsal library.');
    library.current.open=true;
  });}
  async function remove(record){if(!window.confirm(t('Delete this saved rehearsal from this browser?')))return;await work(async()=>{await deleteRehearsal(record.id);await refresh();if(selected===record.id)setSelected('');if(compare===record.id)setCompare('');setNotice('Saved rehearsal deleted from this browser.');});}
  async function clear(){if(!window.confirm(t('Delete all saved rehearsals from this browser? This cannot be undone.')))return;await work(async()=>{await clearRehearsals();await refresh();setSelected('');setCompare('');setNotice('All saved rehearsals deleted from this browser.');});}
  const first=records.find(record=>record.id===selected),second=records.find(record=>record.id===compare);
  return <section className="rehearsal-library" aria-label={t('Rehearsal library')}>
    {current&&<div className="panel library-save"><h2>{t('Remember this rehearsal')}</h2><p>{t('Keep this conversation, feedback and phrases to review your language practice later.')}</p><label>{t('Rehearsal title')}<input maxLength={100} value={title} disabled={pending} onChange={event=>setTitle(event.target.value)}/></label>
      <label className="feedback-consent"><input type="checkbox" checked={consent} disabled={pending} onChange={event=>setConsent(event.target.checked)}/>{t('Save my conversation and review in this browser on this device.')}</label>
      <p className="subtle">{t('Saved copies remain after you delete the server session. Anyone using this browser profile may read them. No original files or audio are saved. You can delete saved copies in your library.')}</p>
      <button className="secondary" type="button" disabled={pending||!consent||!title.trim()} onClick={save}>{pending?t('Saving…'):t('Save rehearsal on this device')}</button>
    </div>}
    <details ref={library} className="panel library-panel"><summary>{t('My saved rehearsals')} ({records.length})</summary>
      <p className="subtle">{t('Only saved on this browser and device. No account or sync. Browser data can be cleared or lost; download important rehearsals as a backup. Saved conversations can be reread, not resumed as live sessions.')}</p>
      {loading?<p role="status">{t('Loading saved rehearsals…')}</p>:!records.length?<p>{t('No saved rehearsals yet. Finish a rehearsal and choose to save it.')}</p>:<>
        <label>{t('Filter saved rehearsals')}<input type="search" value={filter} onChange={event=>setFilter(event.target.value)}/></label>
        <div className="library-list">{records.filter(record=>`${record.title} ${t(record.language)} ${t(labels[record.scenario])}`.toLocaleLowerCase().includes(filter.toLocaleLowerCase())).map(record=><button type="button" className="secondary" key={record.id} aria-pressed={record.id===selected} onClick={()=>{setSelected(record.id);if(compare===record.id)setCompare('');}}>{record.title} · {t(record.language)} · {t('Take')} {record.take}</button>)}</div>
        {first&&<><label>{t('Compare with another rehearsal')}<select value={compare} onChange={event=>setCompare(event.target.value)}><option value="">{t('No comparison')}</option>{records.filter(record=>record.id!==selected).map(record=><option key={record.id} value={record.id}>{record.title} · {t(record.language)} · {t('Take')} {record.take}</option>)}</select></label>
          <div className={'library-reader '+(second?'comparing':'')}><SavedTake record={first} onDelete={remove}/>{second&&<SavedTake record={second} onDelete={remove}/>}</div></>}
        <button className="text-button" type="button" disabled={pending} onClick={clear}>{t('Delete all saved rehearsals')}</button>
      </>}
      {unreadable>0&&<p role="alert">{t('Some saved entries could not be read. Clear the library to remove them.')}</p>}
      {!records.length&&unreadable>0&&<button className="text-button" type="button" disabled={pending} onClick={clear}>{t('Delete all saved rehearsals')}</button>}
    </details>
    {notice&&<p role="status">{t(notice)}</p>}{error&&<p role="alert">{errorText(error)}</p>}
  </section>;
}
