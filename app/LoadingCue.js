'use client';
import {useI18n} from './i18n';
import {useEffect,useState} from 'react';

export function LoadingClapper(){
 return <svg className="loading-clapper" viewBox="0 0 80 72" width="72" height="64" fill="none" aria-hidden="true" focusable="false">
  <rect x="12" y="28" width="56" height="35" rx="7" fill="currentColor"/>
  <g className="loading-clapper-lid"><rect x="12" y="16" width="56" height="13" rx="3" fill="currentColor"/><path d="m22 17 8 11m8-11 8 11m8-11 8 11" stroke="var(--loading-paper, #fffaf0)" strokeWidth="5"/></g>
  <g stroke="var(--loading-paper, #fffaf0)" strokeWidth="3" strokeLinecap="round"><path d="M29 41v2m22-2v2M34 51q6 6 12 0"/></g>
  <path className="loading-clapper-spark" d="M70 7v8m-4-4h8M4 31v6m-3-3h6" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
 </svg>;
}

export default function LoadingCue({label='Setting the stage…'}){
 const {t}=useI18n();
 const [seconds,setSeconds]=useState(0);
 useEffect(()=>{const start=Date.now();const timer=setInterval(()=>setSeconds(Math.floor((Date.now()-start)/1000)),1000);return()=>clearInterval(timer);},[]);
 return <div className="rehearsal-loading" role="status" aria-live="polite"><LoadingClapper/><div><strong>{t(label)}</strong><p>{t("A little backstage preparation. We’ll bring you in when it’s ready.")}</p><p aria-live="off">{t('Waiting: {seconds} seconds. Requests time out after 65 seconds.').replace('{seconds}',seconds)}</p>{seconds>=10&&<p>{t('This is taking longer than usual. If it times out, your draft stays available and you can check the saved conversation.')}</p>}</div></div>;
}
