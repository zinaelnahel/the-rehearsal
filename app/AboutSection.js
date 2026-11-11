'use client';
import {useI18n} from './i18n';
import FilmIcon from './FilmIcon';

const steps=[
 {title:'Bring something real.',body:'Choose a sample or add your own PDF, text, recording or supported video link. Review any transcript, then set your goal and conversation language.'},
 {title:'Try the conversation.',body:'An AI partner plays the other person. Type your replies or use the optional voice mode. Ask questions, practise a boundary, pause or try a different approach.'},
 {title:'Keep what helps.',body:'Review feedback on your actual words, see which goals you practised and replay a moment you want another go at. You choose what to take into real life.'}
];

export default function AboutSection(){
 const {t}=useI18n();
 return <section id="about" className="about-section" aria-labelledby="about-title" tabIndex={-1}>
  <div className="about-heading"><span className="eyebrow">{t('ABOUT THE REHEARSAL')}</span><h2 id="about-title">{t('A rehearsal room for real conversations.')}</h2>
   <p>{t('The flat viewing. The interview. The conversation you have been putting off. A little practice can help you find the words you want to use.')}</p>
  </div>
  <div className="about-layout">
   <div className="about-inspiration">
    <figure className="about-photo"><img src="/images/rehearsal-inspiration.jpg" width="780" height="438" loading="lazy" alt={t('Nathan Fielder wearing a laptop harness in The Rehearsal.')}/><figcaption>{t('Nathan Fielder in The Rehearsal.')} <a href="https://www.slashfilm.com/1894836/nathan-for-you-real/" target="_blank" rel="noreferrer">{t('Image: HBO, via /Film')} ↗</a></figcaption></figure>
    <h3>{t('The idea behind the name.')}</h3>
    <p>{t('In Nathan Fielder’s HBO series The Rehearsal, people prepare for important moments through carefully staged simulations. That idea inspired this project: what if you could try a conversation before having it for real?')}</p>
    <a className="about-series-link" href="https://press.wbd.com/na/property/rehearsal" target="_blank" rel="noreferrer">{t('About the original series')} ↗</a>
    <p className="about-independence">{t('An independent project inspired by the series. No affiliation with Nathan Fielder, HBO or Warner Bros. Discovery.')}</p>
   </div>
   <div className="about-app"><h3>{t('How our app works.')}</h3><p className="about-languages">{t('Practise in English, German or Spanish, with a conversation style and feedback language you choose.')}</p>
    <ol className="about-steps">{steps.map((step,index)=><li key={step.title}><span className="about-step-icon"><FilmIcon step={index===0?0:index===1?2:3}/></span><div><h4>{t(step.title)}</h4><p>{t(step.body)}</p></div></li>)}</ol>
    <div className="about-source-note"><h4>{t('Your context gives the conversation something to work with.')}</h4><p>{t('When a reply uses your source, its citation lets you check the relevant passage or recording timestamp. Missing details should stay unconfirmed. The partner is AI-generated, and real people can respond differently.')}</p></div>
   </div>
  </div>
 </section>;
}
