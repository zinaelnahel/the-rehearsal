'use client';
import {useI18n} from './i18n';

function Commit({value,label,unknown}){
 return /^[a-f0-9]{40}$/i.test(value||'')
  ? <a href={'https://github.com/zinaelnahel/the-rehearsal/commit/'+value} target="_blank" rel="noreferrer" title={label+': '+value}>{value.slice(0,7)}</a>
  : <span>{unknown}</span>;
}

export default function BuildInfo({backend}){
 const {t}=useI18n();
 return <span className="build-info" role="group" aria-label={t('Deployed builds')}>
  <span>{t('UI build')} <Commit value={process.env.NEXT_PUBLIC_BUILD_SHA} label={t('UI build')} unknown={t('Not identified')}/></span>
  <span>{t('API build')} <Commit value={backend} label={t('API build')} unknown={t('Not identified')}/></span>
 </span>;
}
