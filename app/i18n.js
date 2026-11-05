'use client';
import {createContext,useContext,useEffect,useState} from 'react';
import catalog from './locales.json';

const Context=createContext(null);
export function translate(text,locale='en'){
 if(typeof text!=='string'||locale==='en')return text;
 const key=text.trim();
 const value=catalog[key]?.[locale];
 return value?text.replace(key,value):text;
}
export function LanguageProvider({children}){
 const [locale,setLocale]=useState('en');
 useEffect(()=>{document.documentElement.lang=locale;},[locale]);
 const t=text=>translate(text,locale);
 const errorText=text=>!text?text:locale==='en'||catalog[text.trim()]?t(text):t('The request could not be completed. Check your source and connection, then retry. You can paste text instead of importing a file or link.');
 return <Context.Provider value={{locale,setLocale,t,errorText}}>{children}</Context.Provider>;
}
export function useI18n(){return useContext(Context);}
