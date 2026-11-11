'use client';
import {useI18n} from './i18n';
import {useId,useState} from 'react';
import FilmIcon from './FilmIcon';

const scenes=[
 {label:'The flat viewing',line:'Can I ask one more thing?'},
 {label:'The interview',line:'Let me try that again.'},
 {label:'The boundary',line:'This weekend doesn’t work for me.'}
];

export default function RehearsalComic(){
 const {t}=useI18n();
 const [expanded,setExpanded]=useState(false);
 const contentId=useId();
 return <figure className="rehearsal-comic" data-expanded={expanded} aria-label={t('Three illustrated rehearsal scenes: a flat viewing, a job interview, and setting a boundary.')}>
  <div className="comic-masthead"><span><FilmIcon step={2}/>{t('The rehearsal storyboard')}</span><span className="comic-edition" aria-hidden="true">№ 01</span><button type="button" className="comic-toggle" aria-expanded={expanded} aria-controls={contentId} onClick={()=>setExpanded(value=>!value)}>{t(expanded?'Hide comic':'Show comic')}<span aria-hidden="true">{expanded?'−':'+'}</span></button></div>
  <div className="comic-content" id={contentId}>
  <div className="comic-grid" tabIndex={0} role="region" aria-label={t('Rehearsal comic panels')}>{scenes.map((scene,index)=><div className="comic-frame" key={scene.label} style={{'--scene':index}}>
   <img className="comic-art" src="/images/rehearsal-comic-modern.webp" alt="" width="1536" height="1024" loading="lazy" fetchPriority={index===0?'high':undefined}/>
   <p className="comic-bubble"><small>{t('Take 02')}</small>{t(scene.line)}</p>
   <span className="comic-scene-label">{t(scene.label)}</span>
  </div>)}</div>
  <p className="comic-swipe-hint">{t('Swipe or scroll for more scenes.')}</p>
  </div>
  <figcaption><span aria-hidden="true">↳</span><p><s>{t('Umm…')}</s> {t('Try it. Pause. Find your next line.')}</p></figcaption>
 </figure>;
}
