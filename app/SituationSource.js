'use client';
import {useI18n} from './i18n';

export default function SituationSource({kind,onKindChange,text,setText,file,setFile,listingUrl,setListingUrl,listingText,setListingText,disabled,onError}){
 const {t,locale,errorText}=useI18n();

 return <div>
  <label htmlFor="situation-source-kind">{t("How would you like to add context?")}</label>
  <select id="situation-source-kind" value={kind} disabled={disabled} onChange={e=>onKindChange(e.target.value)}>
   <option value="text">{t("Describe your situation or paste text")}</option>
   <option value="file">{t("Upload a document")}</option>
   <option value="listing">{t("Use a listing link (optional)")}</option>
  </select>
  {kind==='text'?<div className="input-area"><label htmlFor="document">{t("Situation notes or document text")}</label><textarea id="document" maxLength={100000} value={text} disabled={disabled} onChange={e=>setText(e.target.value)} rows={8} placeholder={t("Describe the situation, who you are speaking to, and the facts you know. Or paste a document…")}/><small>{text.length.toLocaleString(locale)} {t("/ 100,000 characters")}</small></div>
  :kind==='file'?<div className="upload-area"><span className="upload-icon">↥</span><h3>{t("Your document, your context")}</h3><p>{t("Text-based PDF or DOCX · up to 4 MB")}</p><input id="upload" type="file" accept=".pdf,.docx" disabled={disabled} onChange={e=>{const selected=e.target.files?.[0];if(selected&&selected.size>4*1024*1024){onError('Maximum file size is 4 MB.');e.target.value='';return;}setFile(selected);}}/><p className="subtle">{file?file.name:t("Scanned PDFs are not supported.")}</p></div>
  :<div className="listing-input"><label htmlFor="listing-url">{t("Idealista listing URL")}</label><input id="listing-url" type="url" maxLength={2048} value={listingUrl} disabled={disabled} onChange={e=>setListingUrl(e.target.value)} placeholder={t("https://www.idealista.com/inmueble/…/")}/><p>{t("Spain, Portugal or Italy. Use a direct advert link, not a search page.")}</p><label htmlFor="listing-text">{t("Paste advert text (recommended: Idealista often blocks imports)")}</label><textarea id="listing-text" maxLength={100000} rows={6} value={listingText} disabled={disabled} onChange={e=>setListingText(e.target.value)} placeholder={t("If the site blocks reading, paste the advert’s price, description and features here.")}/><p className="listing-note">{t("Copy the price, description and features from the advert into this field, then select Build my mission again. Your URL stays attached as a reference. Pasted text is used without fetching the page. Otherwise, the server requests the public listing. Blocked pages and login walls are not bypassed.")}</p></div>}
 </div>;
}
