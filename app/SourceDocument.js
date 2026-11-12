'use client';
import {useEffect,useRef,useState} from 'react';
import {api} from './api-client';
import {useI18n} from './i18n';
import {videoEvidence} from './video-evidence.mjs';
import SourceAudio from './SourceAudio';
import {highlightRanges} from './source-highlights.mjs';

function Highlight({text,passage,excerpts,selected}){
 const ranges=selected?highlightRanges(text,passage,excerpts):[];
 const parts=[];let cursor=0;
 for(const [start,end] of ranges){parts.push(text.slice(cursor,start));parts.push(<mark key={start}>{text.slice(start,end)}</mark>);cursor=end;}
 parts.push(text.slice(cursor));return <>{parts}</>;
}

export default function SourceDocument({sessionId,selection,file,onClose}){
 const {t,errorText}=useI18n();
 const dialog=useRef(null),returnFocus=useRef(null),pdfObject=useRef(null),currentSelection=useRef(selection);
 const [audioUrl,setAudioUrl]=useState('');
 useEffect(()=>{if(!file)return;const url=URL.createObjectURL(file);setAudioUrl(url);return()=>{URL.revokeObjectURL(url);setAudioUrl('');};},[file]);
 const [data,setData]=useState(null),[error,setError]=useState(''),[pdf,setPdf]=useState(null),[pdfError,setPdfError]=useState('');
 useEffect(()=>{
  const source=selection?.source;
  currentSelection.current=selection;
  if(!source||videoEvidence(source)){dialog.current?.close();return;}
  const controller=new AbortController();
  returnFocus.current=document.activeElement;
  setData(null);setError('');setPdf(null);setPdfError('');
  dialog.current?.showModal();
  api('/sessions/'+sessionId+'/source/'+encodeURIComponent(source.id),undefined,'GET',controller.signal)
   .then(result=>{if(!controller.signal.aborted)setData(result);})
   .catch(err=>{if(!controller.signal.aborted)setError(err.message);});
  return()=>{controller.abort();if(pdfObject.current){URL.revokeObjectURL(pdfObject.current);pdfObject.current=null;}};
 },[sessionId,selection]);
 useEffect(()=>{
  if(!data)return;
  const frame=requestAnimationFrame(()=>{if(dialog.current?.open)dialog.current.querySelector('mark')?.scrollIntoView({block:'center'});});
  return()=>cancelAnimationFrame(frame);
 },[data]);
 async function openPdf(){
  const activeSelection=selection;
  try{
   const bytes=await file.arrayBuffer();
   if(!dialog.current?.open||activeSelection!==currentSelection.current)return;
   if(pdfObject.current)URL.revokeObjectURL(pdfObject.current);
   pdfObject.current=URL.createObjectURL(new Blob([bytes],{type:'application/pdf'}));
   setPdf(pdfObject.current);
  }catch{setPdfError(t('The original file is unavailable. You can still read the extracted text below.'));}
 }
 return <dialog ref={dialog} className="source-document" aria-labelledby="source-document-title" onClose={()=>{returnFocus.current?.focus();onClose();}}>
  <div className="source-document-heading"><h2 id="source-document-title">{t('View source')}</h2><button type="button" className="secondary" onClick={()=>dialog.current?.close()}>{t('Close source')}</button></div>
  {error?<p role="alert">{errorText(error)}</p>:!data?<p role="status">{t('Loading source…')}</p>:<>
   <p><strong>{data.focus.source}</strong> · {data.focus.location}</p>
   <p className="subtle">{t(selection?.source?.highlights?.length?'The highlighted passage is the evidence used for this reply.':'Source context is shown below. No exact supporting excerpt is available for this reply.')}</p>
   {(data.original_audio_url||data.browser_audio&&audioUrl)&&<SourceAudio url={data.original_audio_url||audioUrl} key={data.focus.id} start={data.focus.start} end={data.focus.end} timed={data.audio_timed&&Number.isFinite(data.focus.start)&&Number.isFinite(data.focus.end)}/>}
   {data.kind==='pdf'&&<>
    <p className="subtle">{t('Extracted page text. The original page layout may differ.')}</p>
    {data.original_pdf_url&&<p><a href={data.original_pdf_url+'#page='+data.page} target="_blank" rel="noreferrer">{t('View original PDF')} ↗</a></p>}
    {file?.name===data.focus.source&&/\.pdf$/i.test(file.name)&&!pdf&&<button type="button" className="secondary" onClick={openPdf}>{t('View original PDF')}</button>}
    {pdf&&<iframe title={t('Original PDF page')} src={pdf+'#page='+data.page}/>}
    {pdfError&&<p role="status">{pdfError}</p>}
   </>}
   <div className="source-document-text">{data.sections.map((section,index)=><section key={index} className={section.selected?'selected-source-section':''}><h3>{section.location}</h3><p><Highlight text={section.text} passage={data.focus.text} excerpts={selection?.source?.highlights||[]} selected={section.selected}/></p></section>)}</div>
  </>}
 </dialog>;
}
