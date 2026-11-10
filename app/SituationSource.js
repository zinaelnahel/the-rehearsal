'use client';
import {useI18n} from './i18n';
export default function SituationSource({kind,onKindChange,text,setText,file,setFile,disabled,onError}){
 const {t,locale}=useI18n();
 return <div>
  <label htmlFor="situation-source-kind">{t('How would you like to add context?')}</label>
  <select id="situation-source-kind" value={kind} disabled={disabled} onChange={e=>onKindChange(e.target.value)}>
   <option value="text">{t('Describe your situation or paste text')}</option>
   <option value="file">{t('Upload a document')}</option>
  </select>
  {kind==='text'?<div className="input-area"><label htmlFor="document">{t('Situation notes or document text')}</label><textarea id="document" maxLength={100000} value={text} disabled={disabled} onChange={e=>setText(e.target.value)} rows={8} placeholder={t('Describe the situation, who you are speaking to, and the facts you know. Or paste a document…')}/><small>{text.length.toLocaleString(locale)} {t('/ 100,000 characters')}</small></div>
  :<div className="upload-area"><span className="upload-icon">↥</span><h3>{t('Your document, your context')}</h3><p>{t('PDF or DOCX · up to 4 MB')}</p><input id="upload" type="file" accept=".pdf,.docx" disabled={disabled} onChange={e=>{const selected=e.target.files?.[0];if(selected&&selected.size>4*1024*1024){onError('Maximum file size is 4 MB.');e.target.value='';return;}setFile(selected);}}/><p className="subtle">{file?.name}</p><p className="subtle">{t('Image-based PDFs use OCR on this server. Review the recognised text before building a mission. Up to 8 image-based pages; no PDF images are sent to OpenAI.')}</p></div>}
 </div>;
}
