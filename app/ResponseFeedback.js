'use client';
import {useI18n} from './i18n';
import {useEffect,useRef,useState} from 'react';
import {api} from './api-client';

const reasons=[['realism','Didn’t feel realistic'],['unanswered','Didn’t answer my question'],['fact','Got a fact wrong'],['tone','Tone felt off'],['speed','Too slow'],['other','Other']];

export default function ResponseFeedback({sessionId,response,saved,onChange,onSessionExpired,sharingEnabled=false,retentionDays=90}) {
 const {t,locale,errorText}=useI18n();

 const [rating,setRating]=useState(saved?.rating??null),[reason,setReason]=useState(saved?.reason??''),[pending,setPending]=useState(false),[notice,setNotice]=useState(saved?.notice??'');
 const [share,setShare]=useState(saved?.shareForImprovement??false);
 const saving=useRef(false);
 useEffect(()=>{if(saved){setRating(saved.rating??null);setReason(saved.reason??'');setShare(saved.shareForImprovement??false);setNotice(saved.notice??'');}},[saved]);
 async function save(next,nextReason='',nextShare=share) {
  if(saving.current)return;
  const previousShare=share;
  saving.current=true;
  setPending(true);
  setShare(!!next&&nextShare);
  try {
   const result=await api(`/sessions/${sessionId}/responses/${response.id}/feedback`,{rating:next,reason:nextReason||null,share_for_improvement:!!next&&nextShare,frontend_build:/^[a-f0-9]{40}$/i.test(process.env.NEXT_PUBLIC_BUILD_SHA||'')?process.env.NEXT_PUBLIC_BUILD_SHA:'unknown'},'PUT');
   if(next&&nextShare&&result.shared!==true)throw Error('Sharing was not confirmed. Please retry or keep your rating in this session.');
   const acknowledgement=next?(result.shared?'Thanks. Your anonymous feedback was saved to help improve the app.':'Thanks. Feedback noted for this session.'):'Feedback cleared, including any shared copy.';
   setRating(next);setReason(nextReason);setShare(!!next&&nextShare);setNotice(acknowledgement);
   onChange?.({rating:next,reason:nextReason,shareForImprovement:!!next&&nextShare,notice:acknowledgement});
  } catch(e) {
   setShare(previousShare);
   if(e.status===404&&e.message.startsWith('Session expired or deleted.'))onSessionExpired?.();
   setNotice(e.message);
  } finally {saving.current=false;setPending(false);}
 }
 return <div className="response-feedback" aria-label={t("Rehearsal feedback")}>
  {sharingEnabled&&<><label className="feedback-consent"><input type="checkbox" checked={share} disabled={pending} onChange={event=>{const checked=event.target.checked;if(rating)void save(rating,reason,checked);else {setShare(checked);onChange?.({rating,reason,shareForImprovement:checked,notice});}}}/>{t('Share my anonymous rating to help improve the app.')}</label><p className="subtle">{t('Shared feedback includes your rating, optional category, scenario, language, app/model version and numeric performance summaries. No conversation, source text, audio or contact details. It may remain for up to {days} days after session deletion. Untick or Clear before leaving this review to remove it.').replace('{days}',String(retentionDays))}</p></>}
  <div className="rating-buttons">{[['up','👍',t("Useful rehearsal")],['down','👎',t("Unhelpful rehearsal")]].map(([value,icon,label])=><button key={value} type="button" aria-label={t(label)} aria-pressed={rating===value} disabled={pending} onClick={()=>save(rating===value?null:value)}><span aria-hidden="true">{icon}</span></button>)}{rating&&<button type="button" disabled={pending} onClick={()=>save(null)}>{t("Clear")}</button>}</div>
  {rating==='down'&&<label className="rating-reason">{t("Reason (optional)")}<select value={reason} disabled={pending} onChange={e=>save('down',e.target.value)}><option value="">{t("No reason")}</option>{reasons.map(([value,label])=><option key={value} value={value}>{t(label)}</option>)}</select></label>}
  <small role="status">{errorText(notice)}</small>
 </div>;
}
