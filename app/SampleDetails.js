'use client';
import {useI18n} from './i18n';
import catalog from '../samples/catalog.json';

export default function SampleDetails({scenario}){
 const {t}=useI18n();
 const sample=catalog[scenario]?.filename?catalog[scenario]:null;
 return <div className="sample-details">
  {sample&&<><p><strong>{sample.publisher}</strong><br/>{t('Original source language:')} {sample.source_language}</p>
   <p className="subtle">{t(sample.note)}</p>
   <p><a href={'/api/samples/'+scenario+'/document'} target="_blank" rel="noreferrer">{t('View original PDF')} ↗</a>{sample.source_url&&<> · <a href={sample.source_url} target="_blank" rel="noreferrer">{t('Publisher source')} ↗</a></>}</p>
   <p className="subtle">{t('Original documents stay in their published language. Choose any supported conversation and feedback language.')}</p></>}

 </div>;
}
