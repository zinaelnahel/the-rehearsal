'use client';
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
 if(connection.status==='ready')return null;
 const failed=connection.status==='failed';
 return <section className="connection-status" aria-label="Practice server connection"><div role="status" aria-live="polite"><strong>{failed?'The practice server could not be reached.':connection.status==='slow'?'Still connecting to the rehearsal room…':'Connecting to the rehearsal room…'}</strong><p>{failed?'Your setup is still here. Retry the connection when you are ready.':connection.status==='slow'?'The free server may be waking after inactivity. You can read a fictional sample while you wait.':'You can prepare your setup while we connect. Practice starts once the server is ready.'}</p></div>{failed&&<button className="secondary" onClick={connection.retry}>Retry connection</button>}<details className="waiting-sample"><summary>Read a sample while you wait</summary><p className="subtle">Fictional source text only. This does not start a rehearsal or send your data.</p><pre>{samples[scenario]?.[language]||samples.apartment.English}</pre></details></section>;
}
