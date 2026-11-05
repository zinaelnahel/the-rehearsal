'use client';
import {useI18n} from './i18n';
export default function ReviewNextStep({goals,busy,onRetry}){
 const {t,locale,errorText}=useI18n();

 const next=goals.find(goal=>['unknown','unverified'].includes(goal.answer_status))||goals.find(goal=>!goal.achieved);
 if(!next)return <section className="panel review-next-step"><div className="eyebrow">{t("YOUR NEXT STEP")}</div><h2>{t("You have practised every goal.")}</h2><p>{t("Keep your notes for real life, or choose a goal below to rehearse again. Practice does not guarantee what the other person will say.")}</p></section>;
 const unanswered=['unknown','unverified'].includes(next.answer_status);
 return <section className="panel review-next-step" aria-labelledby="next-step-heading"><div className="eyebrow">{t("YOUR NEXT STEP")}</div><h2 id="next-step-heading">{unanswered?t("Practise a follow-up."):t("Give this moment another take.")}</h2><p>{unanswered?t("The answer is not confirmed. Practise how you’ll check it in real life."):t("This learner action has not been practised yet.")}</p><strong className="next-goal">{next.text}</strong><button className="primary" disabled={busy} onClick={()=>onRetry(next.id)}>{t("Rehearse this moment")} <span aria-hidden="true">→</span></button><p className="subtle">{t("Replay replaces this take. You can download a copy first; you’ll be asked before continuing.")}</p></section>;
}
