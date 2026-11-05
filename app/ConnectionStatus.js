'use client';
import {useI18n} from './i18n';
import {useEffect,useState} from 'react';
import samples from './sample-previews.json';

export function usePracticeConnection(){
 const [attempt,setAttempt]=useState(0),[state,setState]=useState({status:'connecting',config:null});
 useEffect(()=>{
  let active=true;
  const controller=new AbortController();
  setState({status:'connecting',config:null});
  const slow=setTimeout(()=>{if(active)setState({status:'slow',config:null});},8000);
  const timeout=setTimeout(()=>controller.abort(),55000);
  fetch('/api/config',{cache:'no-store',signal:controller.signal})
   .then(response=>{if(!response.ok)throw Error();return response.json();})
   .then(config=>{if(!['live','demo'].includes(config.mode))throw Error();if(active){clearTimeout(slow);clearTimeout(timeout);setState({status:'ready',config});}})
   .catch(()=>{if(active){clearTimeout(slow);clearTimeout(timeout);setState({status:'failed',config:null});}});
  return()=>{active=false;clearTimeout(slow);clearTimeout(timeout);controller.abort();};
 },[attempt]);
 return {...state,retry:()=>setAttempt(value=>value+1)};
}

export default function ConnectionStatus({connection,scenario,language}){
 const {t,locale,errorText}=useI18n();

 if(connection.status==='ready')return null;
 const failed=connection.status==='failed';
 return <section className="connection-status" aria-label={t("Practice server connection")}><div role="status" aria-live="polite"><strong>{failed?t("The practice server could not be reached."):connection.status==='slow'?t("Still connecting to the rehearsal room…"):t("Connecting to the rehearsal room…")}</strong><p>{failed?t("Your setup is still here. Retry the connection when you are ready."):connection.status==='slow'?t("The free server may be waking after inactivity. You can read a fictional sample while you wait."):t("You can prepare your setup while we connect. Practice starts once the server is ready.")}</p></div>{failed&&<button className="secondary" onClick={connection.retry}>{t("Retry connection")}</button>}<details className="waiting-sample"><summary>{t("Read a sample while you wait")}</summary><p className="subtle">{t("Fictional source text only. This does not start a rehearsal or send your data.")}</p><pre>{samples[scenario]?.[language]||samples.apartment.English}</pre></details></section>;
}
