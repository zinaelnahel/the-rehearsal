'use client';
import {useI18n} from './i18n';
import {useEffect,useId,useRef,useState} from 'react';
import {api} from './api-client';

const reasons=[['realism','Didn’t feel realistic'],['unanswered','Didn’t answer my question'],['fact','Got a fact wrong'],['tone','Tone felt off'],['speed','Too slow'],['other','Other']];
const qualityQuestions=[
 ['relevance','Did the partner respond to what you said?'],
 ['memory','Did the partner remember your earlier answers?'],
 ['continuity','Did the conversation flow naturally?'],
 ['role_consistency','Did the partner stay in character?'],
 ['grounding','Did the details match your source?'],
 ['language_agreement','Did the language and wording sound natural?']
];

export default function ResponseFeedback({sessionId,response,saved,onChange,onSessionExpired,sharingEnabled=false,retentionDays=90}) {
 const {t,locale,errorText}=useI18n();

 const [rating,setRating]=useState(saved?.rating??null),[reason,setReason]=useState(saved?.reason??''),[pending,setPending]=useState(false),[notice,setNotice]=useState(saved?.notice??'');
 const [share,setShare]=useState(saved?.shareForImprovement??false);
 const [quality,setQuality]=useState(saved?.quality??{});
 const saving=useRef(false);
 const qualityPrefix=useId();
 useEffect(()=>{if(saved){setRating(saved.rating??null);setReason(saved.reason??'');setShare(saved.shareForImprovement??false);setNotice(saved.notice??'');setQuality(saved.quality??{});}},[saved]);
 async function save(next,nextReason='',nextShare=share,nextQuality=quality) {
  if(saving.current)return;
  const previousShare=share;
  saving.current=true;
  setPending(true);
  setShare(!!next&&nextShare);
  try {
   const details=next?nextQuality:{};
   const result=await api(`/sessions/${sessionId}/responses/${response.id}/feedback`,{rating:next,reason:nextReason||null,share_for_improvement:!!next&&nextShare,frontend_build:/^[a-f0-9]{40}$/i.test(process.env.NEXT_PUBLIC_BUILD_SHA||'')?process.env.NEXT_PUBLIC_BUILD_SHA:'unknown',...(Object.keys(details).length?{quality:details}:{})},'PUT');
   if(next&&nextShare&&result.shared!==true)throw Error('Sharing was not confirmed. Please retry or keep your rating in this session.');
   const acknowledgement=next?(result.shared?'Thanks. Your anonymous feedback was saved to help improve the app.':'Thanks. Feedback noted for this session.'):'Feedback cleared, including any shared copy.';
   setRating(next);setReason(nextReason);setShare(!!next&&nextShare);setNotice(acknowledgement);setQuality(details);
   onChange?.({rating:next,reason:nextReason,shareForImprovement:!!next&&nextShare,notice:acknowledgement,quality:details});
  } catch(e) {
   setShare(previousShare);
   if(e.status===404&&e.message.startsWith('Session expired or deleted.'))onSessionExpired?.();
   setNotice(e.message);
  } finally {saving.current=false;setPending(false);}
 }
 return <div className="response-feedback" aria-label={t("Rehearsal feedback")}>
  {sharingEnabled&&<><label className="feedback-consent"><input type="checkbox" checked={share} disabled={pending} onChange={event=>{const checked=event.target.checked;if(rating)void save(rating,reason,checked);else {setShare(checked);onChange?.({rating,reason,shareForImprovement:checked,notice,quality});}}}/>{t('Share my anonymous rating to help improve the app.')}</label><p className="subtle">{t('Shared feedback includes your rating, optional category and quality answers, scenario, language, app/model version and numeric performance summaries. No conversation, source text, audio or contact details. It may remain for up to {days} days after session deletion. Untick or Clear before leaving this review to remove it.').replace('{days}',String(retentionDays))}</p></>}
  <div className="rating-buttons">{[['up','👍',t("Useful rehearsal")],['down','👎',t("Unhelpful rehearsal")]].map(([value,icon,label])=><button key={value} type="button" aria-label={t(label)} aria-pressed={rating===value} disabled={pending} onClick={()=>save(rating===value?null:value)}><span aria-hidden="true">{icon}</span></button>)}{rating&&<button type="button" disabled={pending} onClick={()=>save(null)}>{t("Clear")}</button>}</div>
  {rating==='down'&&<label className="rating-reason">{t("Reason (optional)")}<select value={reason} disabled={pending} onChange={e=>save('down',e.target.value)}><option value="">{t("No reason")}</option>{reasons.map(([value,label])=><option key={value} value={value}>{t(label)}</option>)}</select></label>}
  {rating&&response.kind==='dialogue'&&<details className="quality-feedback"><summary>{t('A little more detail (optional)')}</summary><p>{t('Answer any questions you like. Choose Not sure if you cannot judge. Each answer is saved with your rating.')}</p><div className="quality-questions">{qualityQuestions.map(([dimension,label])=><div className="quality-question" key={dimension}><label htmlFor={qualityPrefix+dimension}>{t(label)}</label><select id={qualityPrefix+dimension} value={quality[dimension]??''} disabled={pending} onChange={event=>{const next={...quality};if(event.target.value)next[dimension]=event.target.value;else delete next[dimension];void save(rating,reason,share,next);}}><option value="">{t('Not rated')}</option><option value="pass">{t('Yes')}</option><option value="fail">{t('No')}</option><option value="uncertain">{t('Not sure')}</option></select></div>)}</div></details>}
  <small role="status">{errorText(notice)}</small>
 </div>;
}
