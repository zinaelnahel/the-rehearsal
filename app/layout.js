import './style.css';
import {LanguageProvider} from './i18n';
import './cinematic.css';
import './outcomes.css';
import './inspiration.css';
import './experience.css';
import './voice.css';
import './library.css';
import './loading.css';
import './source-video.css';
export const metadata = {title: 'The Rehearsal — Real life, rehearsed.', description: 'Rehearse real-life situations in English, German or Spanish, with your document as a guide.'};
export default function Layout({children}) {return <html lang="en"><body><LanguageProvider>{children}</LanguageProvider></body></html>}
