'use client';
import {useI18n} from './i18n';
import {useEffect,useState} from 'react';
import samples from './sample-previews.json';
import {LoadingClapper} from './LoadingCue';

export function usePracticeConnection(){
 const [attempt,setAttempt]=useState(0),[state,setState]=useState({status:'connecting',config:null});
 useEffect(()=>{
  let active=true;
  const controller=new AbortController();
  const started=Date.now();
  setState({status:'connecting',config:null,elapsed:0,retrying:false});
  const timer=setInterval(()=>{if(active)setState(previous=>({...previous,elapsed:Math.floor((Date.now()-started)/1000),status:previous.status==='connecting'&&Date.now()-started>=8000?'slow':previous.status}));},1000);
  async function connect(){
   for(let round=0;round<2&&active;round++){
    let timeout;
    let retryable=true;
    const request=new AbortController();
    const cancel=()=>request.abort();
    controller.signal.addEventListener('abort',cancel,{once:true});
    try{
     timeout=setTimeout(cancel,55000);
     const response=await fetch('/api/config',{cache:'no-store',signal:request.signal});
     if(!response.ok){retryable=[502,503,504].includes(response.status);throw Error();}
     const config=await response.json();
     if(!['live','demo'].includes(config.mode)){retryable=false;throw Error();}
     if(active)setState(previous=>({...previous,status:'ready',config}));
     clearInterval(timer);return;
    }catch(error){
     if(!active)return;
     if(round===1||!retryable){setState(previous=>({...previous,status:'failed'}));clearInterval(timer);return;}
     setState(previous=>({...previous,retrying:true}));
    }finally{
     clearTimeout(timeout);controller.signal.removeEventListener('abort',cancel);
    }
   }
   if(active){clearInterval(timer);setState(previous=>({...previous,status:'failed'}));}
  }
  connect();
  return()=>{active=false;clearInterval(timer);controller.abort();};
 },[attempt]);
 return {...state,retry:()=>setAttempt(value=>value+1)};
}

export default function ConnectionStatus({connection,scenario,language}){
 const {t}=useI18n();

 if(connection.status==='ready')return null;
 const failed=connection.status==='failed';
 return <section className="connection-status" aria-label={t("Practice server connection")}><div role="status" aria-live="polite">{!failed&&<div className="connection-loading-heading"><LoadingClapper/><p>{t("Setting the stage…")}</p></div>}<strong>{failed?t("The practice server could not be reached."):connection.status==='slow'?t("Still connecting to the rehearsal room…"):t("Connecting to the rehearsal room…")}</strong><p>{failed?t("Your setup is still here. Retry the connection when you are ready."):connection.status==='slow'?t("The free server may be waking after inactivity. You can read a sample while you wait."):t("You can prepare your setup while we connect. Practice starts once the server is ready.")}</p>{!failed&&<p>{t("Waiting: {seconds} seconds.").replace("{seconds}",connection.elapsed||0)} {connection.retrying?t("Retrying automatically once. Your setup stays here."):t("The first connection can take about a minute after inactivity.")}</p>}</div>{failed&&<button className="secondary" onClick={connection.retry}>{t("Retry connection")}</button>}<details className="waiting-sample"><summary>{t("Read a sample while you wait")}</summary><p className="subtle">{t("Sample preview only. This does not start a rehearsal or send your data.")}</p><pre>{samples[scenario]?.[language]||samples.apartment.English}</pre></details></section>;
}
