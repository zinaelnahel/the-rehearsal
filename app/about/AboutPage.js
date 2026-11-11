'use client';
import {useEffect,useRef} from 'react';
import Link from 'next/link';
import AboutSection from '../AboutSection';
import ThemeControl from '../ThemeControl';
import {useI18n} from '../i18n';
import {useVisitedRehearsal} from '../RehearsalWorkspace';

export default function AboutPage(){
 const {t,locale,setLocale}=useI18n();
 const visited=useVisitedRehearsal(),main=useRef(null);
 useEffect(()=>{if(visited){const heading=main.current?.querySelector('h1');heading?.setAttribute('tabindex','-1');heading?.focus();}},[visited]);
 const back=visited?'Back to rehearsal':'Try a rehearsal';
 return <div className="app about-page">
  <a className="skip-link" href="#about-main">{t('Skip to main content')}</a>
  <header className="topbar"><Link href="/" className="brand" aria-label={t('The Rehearsal home')}><span className="brand-symbol">R<span>·</span></span>{t('The Rehearsal')}</Link>
   <div className="header-right"><ThemeControl/><label className="interface-language">{t('Interface language')}<select aria-label={t('Interface language')} value={locale} onChange={event=>setLocale(event.target.value)}><option value="en">English</option><option value="de">Deutsch</option><option value="es">Español</option></select></label><Link href="/about" className="about-link" aria-current="page">{t('About')}</Link></div>
  </header>
  <main id="about-main" ref={main} tabIndex={-1}><Link href="/" className="about-back">← {t(back)}</Link><AboutSection/><Link href="/" className="secondary about-return">← {t(back)}</Link></main>
  <footer><span className="footer-brand">{t('The Rehearsal')}</span><span>{t('An independent real-life rehearsal experiment.')}</span><Link href="/">{t(back)}</Link></footer>
 </div>;
}
