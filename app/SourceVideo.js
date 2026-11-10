'use client';
import {useEffect,useRef,useState} from 'react';
import {useI18n} from './i18n';
import {videoEvidence,videoTime} from './video-evidence.mjs';

export default function SourceVideo({url,selection}){
 const {t}=useI18n();
 const [loaded,setLoaded]=useState(false);
 const panel=useRef(null);
 const source=selection?.source||{url};
 const video=videoEvidence(source);
 useEffect(()=>{
  if(selection){setLoaded(true);panel.current?.scrollIntoView({block:'nearest',behavior:'instant'});}
 },[selection]);
 if(!video)return null;
 return <section className="panel source-video" ref={panel} aria-label={t('Source video')}>
  <h2>{t('Source video')}</h2>
  <p>{t('Choose “Watch this part” on a cited passage to view its timestamp in the video.')}</p>
  {video.timed&&<p role="status">{t('Selected video section:')} {videoTime(source.start)}{video.end!==null?'–'+videoTime(source.end):''}</p>}
  {selection?.source?.text&&<blockquote>{source.text}</blockquote>}
  {loaded?<iframe key={selection?.nonce||'full'} title={t('Source video')} src={video.embed} allow="encrypted-media; picture-in-picture; fullscreen" allowFullScreen referrerPolicy="strict-origin-when-cross-origin"/>:<button type="button" className="secondary" onClick={()=>setLoaded(true)}>{t('Load source video')}</button>}
  <p className="subtle">{t('Loading the player connects to YouTube. If playback is unavailable here, open the selected part on YouTube.')}</p>
  <a href={video.external} target="_blank" rel="noreferrer">{t('Open on YouTube ↗')}{video.timed?' · '+videoTime(source.start):''}</a>
 </section>;
}
