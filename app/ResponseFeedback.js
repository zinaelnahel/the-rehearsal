'use client';
import {useI18n} from './i18n';
import {useState} from 'react';
import {api} from './api-client';

const reasons=[['realism','Didn’t feel realistic'],['unanswered','Didn’t answer my question'],['fact','Got a fact wrong'],['tone','Tone felt off'],['other','Other']];

export default function ResponseFeedback({sessionId,response,saved,onChange,onSessionExpired}) {
 const {t,locale,errorText}=useI18n();

 const [rating,setRating]=useState(saved?.rating??null),[reason,setReason]=useState(saved?.reason??''),[pending,setPending]=useState(false),[notice,setNotice]=useState(saved?.notice??'');
 async function save(next,nextReason='') {
  if(pending)return;
  setPending(true);
  try {
   await api(`/sessions/${sessionId}/responses/${response.id}/feedback`,{rating:next,reason:nextReason||null},'PUT');
   const acknowledgement=next?'Thanks. Feedback noted for this session.':'Feedback cleared.';
   setRating(next);setReason(nextReason);setNotice(acknowledgement);
   onChange?.({rating:next,reason:nextReason,notice:acknowledgement});
  } catch(e) {
   if(e.status===404&&e.message.startsWith('Session expired or deleted.'))onSessionExpired?.();
   setNotice(e.message);
  } finally {setPending(false);}
 }
 return <div className="response-feedback" aria-label={t("Rehearsal feedback")}>
  <div className="rating-buttons">{[['up','👍',t("Useful rehearsal")],['down','👎',t("Unhelpful rehearsal")]].map(([value,icon,label])=><button key={value} type="button" aria-label={t(label)} aria-pressed={rating===value} disabled={pending} onClick={()=>save(rating===value?null:value)}><span aria-hidden="true">{icon}</span></button>)}{rating&&<button type="button" disabled={pending} onClick={()=>save(null)}>{t("Clear")}</button>}</div>
  {rating==='down'&&<label className="rating-reason">{t("Reason (optional)")}<select value={reason} disabled={pending} onChange={e=>save('down',e.target.value)}><option value="">{t("No reason")}</option>{reasons.map(([value,label])=><option key={value} value={value}>{t(label)}</option>)}</select></label>}
  <small role="status">{errorText(notice)}</small>
 </div>;
}
