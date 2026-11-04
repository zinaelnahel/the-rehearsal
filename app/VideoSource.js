'use client';
import {useEffect,useRef,useState} from 'react';
import {api} from './api-client';

export default function VideoSource({language,disabled,onChange}){
 const [url,setUrl]=useState(''),[consent,setConsent]=useState(false),[result,setResult]=useState(null),[confirmed,setConfirmed]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const mounted=useRef(true);
 const [pasted,setPasted]=useState(''),[pasteConfirmed,setPasteConfirmed]=useState(false);
 const [useClip,setUseClip]=useState(false),[clipStart,setClipStart]=useState('0'),[clipSeconds,setClipSeconds]=useState('120'),[page,setPage]=useState(0);
 let youtube=false;try{youtube=['youtube.com','www.youtube.com','m.youtube.com','youtu.be','www.youtu.be'].includes(new URL(url).hostname);}catch{}
 useEffect(()=>{mounted.current=true;onChange(null);return()=>{mounted.current=false;};},[]);
 function clear(){setResult(null);setConfirmed(false);setPasteConfirmed(false);setPage(0);onChange(null);}
 async function load(){
  if(busy||disabled||!consent||!url.trim())return;
  if(useClip&&!youtube&&(!clipStart.trim()||!clipSeconds.trim()||!Number.isFinite(Number(clipStart))||Number(clipStart)<0||Number(clipStart)>86400||!Number.isFinite(Number(clipSeconds))||Number(clipSeconds)<1||Number(clipSeconds)>120)){setError('Choose a clip start between 0 and 86,400 seconds and a duration between 1 and 120 seconds.');return;}
  clear();setBusy(true);setError('');
  try{const next=await api('/video/transcript',{url:url.trim(),language,consent:true,...(useClip&&!youtube?{clip_start:Number(clipStart),clip_seconds:Number(clipSeconds)}:{})});if(mounted.current)setResult(next);}
  catch(e){if(mounted.current)setError(e.message);}
  finally{if(mounted.current)setBusy(false);}
 }
 function edit(index,text){setResult({...result,segments:result.segments.map((segment,i)=>i===index?{...segment,text}:segment)});setConfirmed(false);setPasteConfirmed(false);onChange(null);}
 return <div className="transcript-editor">
  <label htmlFor="video-url">Public video URL</label><input id="video-url" type="url" maxLength={2048} placeholder="https://example.com/video.mp4 or a YouTube video link" value={url} disabled={disabled||busy} onChange={e=>{setUrl(e.target.value);clear();setError('');}}/>
  <p>YouTube: full available captions in {language}, up to 100,000 characters. Direct MP4, WebM or MOV files: up to 4 MB; transcribe a short video or choose a clip of up to two minutes from a longer one. Audio is sent to OpenAI. Other video-hosting pages are not supported.</p>
  {!youtube&&<><label className="speech-consent"><input type="checkbox" checked={useClip} disabled={disabled||busy} onChange={e=>{setUseClip(e.target.checked);clear();}}/> Choose a clip from a longer direct video</label>
  {useClip&&<div className="fields"><label htmlFor="clip-start">Start time (seconds)<input id="clip-start" type="number" min="0" max="86400" step="0.1" value={clipStart} disabled={disabled||busy} onChange={e=>{setClipStart(e.target.value);clear();}}/></label><label htmlFor="clip-seconds">Clip duration (seconds)<input id="clip-seconds" type="number" min="1" max="120" step="0.1" value={clipSeconds} disabled={disabled||busy} onChange={e=>{setClipSeconds(e.target.value);clear();}}/></label></div>}</>}
  <label className="speech-consent"><input type="checkbox" checked={consent} disabled={disabled||busy} onChange={e=>setConsent(e.target.checked)}/> I agree to fetch this public video or its captions and send direct-video audio to OpenAI.</label>
  <button className="secondary" type="button" disabled={disabled||busy||!consent||!url.trim()} onClick={load}>{busy?'Importing transcript…':'Import video transcript'}</button>
  {busy&&<p role="status">Preparing the transcript. No rehearsal has been created yet.</p>}{error&&<p role="alert">{error}</p>}
  <details className="pasted-video-transcript" key={error?'failed-import':'manual-import'} open={error?true:undefined}><summary>Have the transcript? Paste it here</summary><p>On YouTube, open the video description and choose Show transcript if available. Copy the transcript and paste it below. This also works when YouTube blocks automatic import.</p><label htmlFor="pasted-video-transcript">Transcript text</label><textarea id="pasted-video-transcript" rows={7} maxLength={100000} value={pasted} disabled={disabled||busy} onChange={e=>{setPasted(e.target.value);setPasteConfirmed(false);setConfirmed(false);onChange(null);}}/><p className="subtle">User-provided text, not fetched or verified against the video. Citations use text sections, not generated timestamps. Text is sent to the server only when you build your mission.</p><label className="speech-consent"><input type="checkbox" checked={pasteConfirmed} disabled={disabled||busy||!pasted.trim()||!url.trim()} onChange={e=>{setPasteConfirmed(e.target.checked);setConfirmed(false);onChange(e.target.checked?{transcript_text:pasted,source_url:url.trim(),source_method:'pasted_transcript'}:null);}}/> I reviewed this pasted transcript and want to use it as my source.</label></details>
  {result&&<><h3>Review the video transcript</h3><p>{result.notice} {result.source_method==='youtube_captions'&&(result.is_generated?'These are automatically generated captions.':'These are published captions.')}</p>
   <a href={result.source_url} target="_blank" rel="noreferrer">View source video ↗</a>
   <p>{result.segments.length} timestamp blocks. {result.segments.reduce((total,s)=>total+s.text.length,0).toLocaleString()} / 100,000 characters.</p>
   {result.segments.slice(page*20,page*20+20).map((segment,offset)=>{const index=page*20+offset;return <label key={index}>{segment.start.toFixed(2)}s–{segment.end.toFixed(2)}s<textarea value={segment.text} maxLength={4000} disabled={disabled||busy} onChange={e=>edit(index,e.target.value)}/></label>;})}
   {result.segments.length>20&&<div className="speech-actions"><button type="button" className="secondary" disabled={disabled||busy||page===0} onClick={()=>setPage(p=>p-1)}>Previous transcript page</button><span role="status">Page {page+1} of {Math.ceil(result.segments.length/20)}</span><button type="button" className="secondary" disabled={disabled||busy||(page+1)*20>=result.segments.length} onClick={()=>setPage(p=>p+1)}>Next transcript page</button></div>}
   <label className="speech-consent"><input type="checkbox" checked={confirmed} disabled={disabled||busy||result.segments.some(s=>!s.text.trim())||result.segments.reduce((total,s)=>total+s.text.length,0)>100000} onChange={e=>{setConfirmed(e.target.checked);setPasteConfirmed(false);onChange(e.target.checked?result:null);}}/> I reviewed this transcript and want to use it as my source.</label>
  </>}
 </div>;
}
