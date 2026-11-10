'use client';
import {useEffect,useRef,useState} from 'react';
import {useI18n} from './i18n';

export default function DocumentReview({preview,busy,error,onConfirm,onCancel}){
 const {t,errorText}=useI18n();
 const dialog=useRef(null);
 const [texts,setTexts]=useState(()=>preview.pages.map(page=>page.text)),[confirmed,setConfirmed]=useState(false),[page,setPage]=useState(0);
 useEffect(()=>{const node=dialog.current;node.showModal();return()=>node.close();},[]);
 const count=texts.reduce((total,text)=>total+text.length,0);
 return <dialog ref={dialog} className="source-document document-review" aria-labelledby="document-review-title" onCancel={event=>{event.preventDefault();if(!busy)onCancel();}}>
  <div className="source-document-heading"><h2 id="document-review-title">{t('Review recognised PDF text')}</h2><button type="button" className="secondary" disabled={busy} onClick={onCancel}>{t('Cancel document import')}</button></div>
  <p><strong>{preview.name}</strong></p>
  {error&&<p role="alert">{errorText(error)}</p>}
  <p>{t('OCR can misread prices, dates and names. Compare this text with your PDF and correct any mistakes. No mission has been created from this document yet.')}</p>
  <p className="subtle">{t('PDF images stay on this server for OCR. In live mode, the reviewed text will be sent to OpenAI when you build the mission.')}</p>
  <label htmlFor="ocr-page-text">{preview.pages[page].location}<textarea id="ocr-page-text" rows={14} maxLength={100000} value={texts[page]} disabled={busy} onChange={event=>{setTexts(previous=>previous.map((text,index)=>index===page?event.target.value:text));setConfirmed(false);}}/></label>
  {texts.length>1&&<div className="speech-actions"><button type="button" className="secondary" disabled={busy||page===0} onClick={()=>setPage(value=>value-1)}>{t('Previous PDF page')}</button><span>{t('Page')} {page+1} {t('of')} {texts.length}</span><button type="button" className="secondary" disabled={busy||page===texts.length-1} onClick={()=>setPage(value=>value+1)}>{t('Next PDF page')}</button></div>}
  <p className="subtle">{count.toLocaleString()} {t('/ 100,000 characters')}</p>
  <label className="speech-consent"><input type="checkbox" checked={confirmed} disabled={busy||!texts.some(text=>text.trim())||count>100000} onChange={event=>setConfirmed(event.target.checked)}/> {t('I reviewed this OCR text and want to use it as my source.')}</label>
  <button type="button" className="primary full" disabled={busy||!confirmed||count>100000} onClick={()=>onConfirm(texts)}>{busy?t('Preparing your rehearsal…'):t('Use reviewed text and build mission')}</button>
 </dialog>;
}
