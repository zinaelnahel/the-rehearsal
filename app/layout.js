import './style.css';
import {LanguageProvider} from './i18n';
import RehearsalWorkspace from './RehearsalWorkspace';
import './cinematic.css';
import './outcomes.css';
import './experience.css';
import './voice.css';
import './library.css';
import './loading.css';
import './source-video.css';
import './source-document.css';
import './practice-ux.css';
import './studio.css';
import './about.css';
import './accessibility.css';
const themeScript=`try{var t=localStorage.getItem('rehearsal-theme');if(!['light','dark','system'].includes(t))t='system';document.documentElement.dataset.theme=t==='system'?(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'):t;}catch(e){document.documentElement.dataset.theme=matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';}`;
export const metadata = {title: 'The Rehearsal — Real life, rehearsed.', description: 'Rehearse real-life situations in English, German or Spanish, with your document as a guide.'};
export default function Layout({children}) {return <html lang="en" suppressHydrationWarning><head><script dangerouslySetInnerHTML={{__html:themeScript}}/></head><body><LanguageProvider><RehearsalWorkspace>{children}</RehearsalWorkspace></LanguageProvider></body></html>}
