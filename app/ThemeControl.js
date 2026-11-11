'use client';
import {useEffect,useState} from 'react';
import {useI18n} from './i18n';

export default function ThemeControl(){
 const {t}=useI18n();
 const [preference,setPreference]=useState('system');
 const [ready,setReady]=useState(false);
 useEffect(()=>{try{const saved=localStorage.getItem('rehearsal-theme');if(['light','dark','system'].includes(saved))setPreference(saved);}catch{}setReady(true);},[]);
 useEffect(()=>{
  if(!ready)return;
  const media=matchMedia('(prefers-color-scheme: dark)');
  const apply=()=>{document.documentElement.dataset.theme=preference==='system'?(media.matches?'dark':'light'):preference;};
  apply();media.addEventListener('change',apply);
  return()=>media.removeEventListener('change',apply);
 },[preference,ready]);
 function change(value){setPreference(value);try{localStorage.setItem('rehearsal-theme',value);}catch{}}
 return <label className="theme-control">{t('Appearance')}<select aria-label={t('Appearance')} value={preference} onChange={event=>change(event.target.value)}><option value="system">{t('System')}</option><option value="light">{t('Light')}</option><option value="dark">{t('Dark')}</option></select></label>;
}
