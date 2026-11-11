'use client';
import {useRef,useState} from 'react';
import {useI18n} from './i18n';
import {videoTime} from './video-evidence.mjs';

export default function SourceAudio({start,end,timed,url='/api/samples/difficult/audio'}){
 const {t}=useI18n();
 const player=useRef(null);
 const [error,setError]=useState('');
 async function play(){
  try{
   const audio=player.current;
   if(audio.readyState===0){
    await new Promise((resolve,reject)=>{
     audio.addEventListener('loadedmetadata',resolve,{once:true});
     audio.addEventListener('error',reject,{once:true});
     audio.load();
    });
   }
   audio.currentTime=timed?start:0;
   await audio.play();
  }catch{setError(t('Audio could not be played. You can still read the source text.'));}
 }
 return <div className="source-audio">
  {timed?<p>{t('Audio excerpt:')} {videoTime(start)}–{videoTime(end)}</p>:<p>{t('This transcript was edited. Play the full voice message; its text has no verified audio timestamps.')}</p>}
  <audio ref={player} controls preload="metadata" src={url} aria-label={t('Original voice message')} onTimeUpdate={()=>{if(timed&&player.current.currentTime>=end)player.current.pause();}}/>
  <p><button type="button" className="secondary" onClick={play}>{t(timed?'Play this excerpt':'Play full voice message')}</button></p>
  {error&&<p role="status">{error}</p>}
 </div>;
}
