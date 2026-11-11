'use client';
import {useI18n} from './i18n';
import FilmIcon from './FilmIcon';

const scenes=[
 {label:'The flat viewing',line:'Can I ask one more thing?'},
 {label:'The interview',line:'Let me try that again.'},
 {label:'The boundary',line:'This weekend doesn’t work for me.'}
];

export default function RehearsalComic(){
 const {t}=useI18n();
 return <figure className="rehearsal-comic" aria-label={t('Three illustrated rehearsal scenes: a flat viewing, a job interview, and setting a boundary.')}>
  <div className="comic-masthead"><span><FilmIcon step={2}/>{t('The rehearsal storyboard')}</span><span className="comic-edition" aria-hidden="true">№ 01</span></div>
  <div className="comic-grid">{scenes.map((scene,index)=><div className="comic-frame" key={scene.label} style={{'--scene':index}}>
   <img className="comic-art" src="/images/rehearsal-comic.webp" alt="" width="1536" height="1024" fetchPriority={index===0?'high':undefined}/>
   <p className="comic-bubble"><small>{t('Take 02')}</small>{t(scene.line)}</p>
   <span className="comic-scene-label">{t(scene.label)}</span>
  </div>)}</div>
  <figcaption><span aria-hidden="true">↳</span><p><s>{t('Umm…')}</s> {t('Try it. Pause. Find your next line.')}</p></figcaption>
 </figure>;
}
