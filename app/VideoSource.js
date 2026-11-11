'use client';
import {useI18n} from './i18n';
import {useEffect,useRef,useState} from 'react';
import {api} from './api-client';
import {videoTime} from './video-evidence.mjs';
import catalog from '../samples/catalog.json';

export default function VideoSource({language,disabled,onChange,initialUrl=''}){
 const {t,locale,errorText}=useI18n();

 const [url,setUrl]=useState(initialUrl),[consent,setConsent]=useState(false),[result,setResult]=useState(null),[confirmed,setConfirmed]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const [range,setRange]=useState(null);
 const mounted=useRef(true);
 const previousLanguage=useRef(language),requestVersion=useRef(0);
 const [languageNotice,setLanguageNotice]=useState(false);
 useEffect(()=>{if(previousLanguage.current!==language){previousLanguage.current=language;requestVersion.current++;setResult(null);setConfirmed(false);setPasteConfirmed(false);setBusy(false);setLanguageNotice(true);setRange(null);setPage(0);onChange(null);}},[language]);
 const [pasted,setPasted]=useState(''),[pasteConfirmed,setPasteConfirmed]=useState(false);
 const [useClip,setUseClip]=useState(false),[clipStart,setClipStart]=useState('0'),[clipSeconds,setClipSeconds]=useState('120'),[page,setPage]=useState(0);
 let youtube=false;try{youtube=['youtube.com','www.youtube.com','m.youtube.com','youtu.be','www.youtu.be'].includes(new URL(url).hostname);}catch{}
 useEffect(()=>{mounted.current=true;onChange(null);return()=>{mounted.current=false;};},[]);
 function clear(){setRange(null);setResult(null);setConfirmed(false);setPasteConfirmed(false);setPage(0);onChange(null);}
 async function load(){
  if(busy||disabled||!consent||!url.trim())return;
  if(useClip&&!youtube&&(!clipStart.trim()||!clipSeconds.trim()||!Number.isFinite(Number(clipStart))||Number(clipStart)<0||Number(clipStart)>86400||!Number.isFinite(Number(clipSeconds))||Number(clipSeconds)<1||Number(clipSeconds)>120)){setError('Choose a clip start between 0 and 86,400 seconds and a duration between 1 and 120 seconds.');return;}
  clear();setBusy(true);setError('');const version=++requestVersion.current;
  try{const next=await api('/video/transcript',{url:url.trim(),language,consent:true,...(useClip&&!youtube?{clip_start:Number(clipStart),clip_seconds:Number(clipSeconds)}:{})});if(mounted.current&&version===requestVersion.current)setResult(next);}
  catch(e){if(mounted.current&&version===requestVersion.current)setError(e.message);}
  finally{if(mounted.current&&version===requestVersion.current)setBusy(false);}
 }
 function edit(index,text){setResult({...result,segments:result.segments.map((segment,i)=>i===index?{...segment,text}:segment)});setConfirmed(false);setPasteConfirmed(false);onChange(null);}
 function choose(start,end){setRange(start===null?null:{start,end});setConfirmed(false);setPasteConfirmed(false);onChange(null);}
 const selectedSegments=result?.segments.slice(range?.start??0,range?range.end+1:undefined)||[];
 return <div className="transcript-editor">
  {languageNotice&&<p role="status">{t("Conversation language changed to")} {t(language)}{t(". Your URL, pasted text and fetch consent were kept. Import captions in this language again, or review and confirm your pasted transcript. Caption availability depends on the video.")}</p>}
  <label htmlFor="video-url">{t("Public video URL (optional for pasted transcripts)")}</label><input id="video-url" type="url" maxLength={2048} placeholder={t("https://example.com/video.mp4 or a YouTube video link")} value={url} disabled={disabled||busy} onChange={e=>{setUrl(e.target.value);clear();setError('');}}/>
  {url.trim()===catalog.video.source_url&&<p className="subtle">{t('Open the source video to watch it or copy its transcript into the field below.')} <a href={catalog.video.transcript_url} target="_blank" rel="noreferrer">{t('Open video and captions')} ↗</a></p>}
  <div className="video-import-summary"><p><strong>YouTube:</strong> {t("Import available captions in")} {t(language)}.</p><p>{t("Video files: MP4, WebM or MOV, up to 4 MB and a two-minute clip. Audio is sent to OpenAI for transcription.")}</p></div>
  <details className="video-import-details"><summary>{t("Import details and privacy")}</summary><p>{t("YouTube imports existing captions only, up to 100,000 characters. If enabled, Supadata may handle blocked caption requests; no AI-generated transcript is requested. Other video-hosting pages are not supported.")}</p></details>
  {!youtube&&<><label className="speech-consent"><input type="checkbox" checked={useClip} disabled={disabled||busy} onChange={e=>{setUseClip(e.target.checked);clear();}}/> {t("Choose a clip from a longer direct video")}</label>
  {useClip&&<div className="fields"><label htmlFor="clip-start">{t("Start time (seconds)")}<input id="clip-start" type="number" min="0" max="86400" step="0.1" value={clipStart} disabled={disabled||busy} onChange={e=>{setClipStart(e.target.value);clear();}}/></label><label htmlFor="clip-seconds">{t("Clip duration (seconds)")}<input id="clip-seconds" type="number" min="1" max="120" step="0.1" value={clipSeconds} disabled={disabled||busy} onChange={e=>{setClipSeconds(e.target.value);clear();}}/></label></div>}</>}
  <label className="speech-consent"><input type="checkbox" checked={consent} disabled={disabled||busy} onChange={e=>setConsent(e.target.checked)}/> {t("I agree to fetch this public video or its captions and send direct-video audio to OpenAI.")} {t("YouTube caption requests may use Supadata if enabled.")}</label>
  <button className="secondary" type="button" disabled={disabled||busy||!consent||!url.trim()} onClick={load}>{busy?t("Importing transcript…"):t("Import video transcript")}</button>
  {busy&&<p role="status">{t("Preparing the transcript. No rehearsal has been created yet.")}</p>}{error&&<p role="alert">{errorText(error)}</p>}
  <details className="pasted-video-transcript" key={error?'failed-import':'manual-import'} open={error?true:undefined}><summary>{t("Have the transcript? Paste it here")}</summary><p>{t("On YouTube, open the video description and choose Show transcript if available. Copy the transcript and paste it below. This also works when YouTube blocks automatic import.")}</p><label htmlFor="pasted-video-transcript">{t("Transcript text")}</label><textarea id="pasted-video-transcript" rows={7} maxLength={100000} value={pasted} disabled={disabled||busy} onChange={e=>{setPasted(e.target.value);setPasteConfirmed(false);setConfirmed(false);onChange(null);}}/><p className="subtle">{t("User-provided text, not fetched or verified against the video. Citations use text sections, not generated timestamps. Text is sent to the server only when you build your mission.")}</p>{!pasted.trim()&&<p id="paste-confirmation-help" className="subtle">{t("Paste transcript text above to enable confirmation. A video link is optional.")}</p>}<label className="speech-consent"><input type="checkbox" checked={pasteConfirmed} disabled={disabled||busy||!pasted.trim()} onChange={e=>{setPasteConfirmed(e.target.checked);setConfirmed(false);onChange(e.target.checked?{transcript_text:pasted,source_url:url.trim(),source_method:'pasted_transcript'}:null);}}/> {t("I reviewed this pasted transcript and want to use it as my source.")}</label></details>
  {result&&<><h3>{t("Review the video transcript")}</h3><p>{t(result.notice)} {result.source_method==='youtube_captions'&&(result.is_generated?t("These are automatically generated captions."):t("These are published captions."))}</p>
   <a href={result.source_url} target="_blank" rel="noreferrer">{t("View source video ↗")}</a>
   <p>{result.segments.length} {t("timestamp blocks.")} {result.segments.reduce((total,s)=>total+s.text.length,0).toLocaleString(locale)} {t("/ 100,000 characters.")}</p>
   <div className="caption-scope"><strong>{range?t('Selected section'):t('Using the full transcript')}</strong>{range&&<> · {videoTime(selectedSegments[0].start)}–{videoTime(selectedSegments.at(-1).end)} · {selectedSegments.length} {t('timestamp blocks.')}</>}<p>{t('Choose a single caption, or use Start here and End here to select a longer section across transcript pages.')}</p>{range&&<><p>{t('Only the selected captions will be used for your mission. Their original timestamps are kept.')}</p><button type="button" className="secondary" disabled={disabled||busy} onClick={()=>choose(null,null)}>{t('Use full transcript')}</button></>}</div>
   {result.segments.slice(page*20,page*20+20).map((segment,offset)=>{const index=page*20+offset;return <div key={index} className={range&&(index<range.start||index>range.end)?'caption-excluded':''}><label>{segment.start.toFixed(2)}s–{segment.end.toFixed(2)}s<textarea value={segment.text} maxLength={4000} disabled={disabled||busy} onChange={e=>edit(index,e.target.value)}/></label><div className="caption-section-controls"><button type="button" className="secondary" disabled={disabled||busy} onClick={()=>choose(index,index)}>{t('Use this section')}</button><button type="button" className="secondary" disabled={disabled||busy} onClick={()=>choose(index,Math.max(index,range?.end??index))}>{t('Start here')}</button><button type="button" className="secondary" disabled={disabled||busy} onClick={()=>choose(Math.min(index,range?.start??index),index)}>{t('End here')}</button></div></div>;})}
   {result.segments.length>20&&<div className="speech-actions"><button type="button" className="secondary" disabled={disabled||busy||page===0} onClick={()=>setPage(p=>p-1)}>{t("Previous transcript page")}</button><span role="status">{t("Page")} {page+1} {t("of")} {Math.ceil(result.segments.length/20)}</span><button type="button" className="secondary" disabled={disabled||busy||(page+1)*20>=result.segments.length} onClick={()=>setPage(p=>p+1)}>{t("Next transcript page")}</button></div>}
   <label className="speech-consent"><input type="checkbox" checked={confirmed} disabled={disabled||busy||selectedSegments.some(s=>!s.text.trim())||selectedSegments.reduce((total,s)=>total+s.text.length,0)>100000} onChange={e=>{setConfirmed(e.target.checked);setPasteConfirmed(false);onChange(e.target.checked?{...result,segments:selectedSegments}:null);}}/> {t("I reviewed this transcript and want to use it as my source.")}</label>
  </>}
 </div>;
}
