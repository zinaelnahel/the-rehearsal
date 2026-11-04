'use client';
import {useEffect,useRef,useState} from 'react';
import {api} from './api-client';

export function SpeechInput({language,disabled=false,onTranscript,onBegin}) {
 const [consent,setConsent]=useState(false),[recording,setRecording]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const recorder=useRef(null),stream=useRef(null),timer=useRef(null),mounted=useRef(true),pending=useRef(false),cancelled=useRef(false);
 function release(){clearTimeout(timer.current);stream.current?.getTracks().forEach(t=>t.stop());stream.current=null;}
 useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;cancelled.current=true;if(recorder.current?.state==='recording')recorder.current.stop();release();};},[]);
 useEffect(()=>{if(disabled){cancelled.current=true;if(recorder.current?.state==='recording')recorder.current.stop();release();}},[disabled]);
 async function transcribe(file){
  if(!file||!consent||pending.current)return;
  if(file.size>4*1024*1024){setError('Maximum media size is 4 MB. Choose a shorter recording.');return;}
  onBegin?.();pending.current=true;setBusy(true);setError('');
  try{const form=new FormData();form.append('file',file,file.name);form.append('language',language);form.append('consent','true');const result=await api('/speech/transcribe',form);if(mounted.current&&!cancelled.current)onTranscript(result);}
  catch(e){if(mounted.current)setError(e.message);}
  finally{pending.current=false;if(mounted.current)setBusy(false);}
 }
 async function record(){
  if(recording){recorder.current?.stop();return;}
  onBegin?.();setError('');cancelled.current=false;
  try{
   if(!navigator.mediaDevices?.getUserMedia||!window.MediaRecorder)throw Error('Microphone recording is unavailable. Upload a recording or type instead.');
   setBusy(true);stream.current=await navigator.mediaDevices.getUserMedia({audio:true});
   if(!mounted.current||cancelled.current){release();return;}
   const mime=['audio/webm','audio/mp4','audio/ogg'].find(type=>MediaRecorder.isTypeSupported(type));
   if(!mime)throw Error('This browser cannot record a supported audio format. Upload a file instead.');
   const active=new MediaRecorder(stream.current,{mimeType:mime,audioBitsPerSecond:64000});recorder.current=active;
   const chunks=[];let size=0,tooLarge=false;
   active.ondataavailable=e=>{if(e.data.size){size+=e.data.size;if(size>4*1024*1024){tooLarge=true;if(active.state==='recording')active.stop();}else chunks.push(e.data);}};
   active.onstop=()=>{release();if(mounted.current)setRecording(false);if(!mounted.current||cancelled.current)return;if(tooLarge){setError('Recording exceeded 4 MB. Try a shorter recording.');return;}const ext=mime.includes('mp4')?'m4a':mime.includes('ogg')?'ogg':'webm';transcribe(new File(chunks,'microphone.'+ext,{type:mime}));};
   active.onerror=()=>{cancelled.current=true;release();setRecording(false);setError('Microphone recording failed. Try uploading a file or type instead.');};
   active.start(500);setRecording(true);timer.current=setTimeout(()=>{if(active.state==='recording')active.stop();},115000);
  }catch(e){release();if(mounted.current)setError(e.name==='NotAllowedError'?'Microphone permission was denied. Upload a recording or type instead.':e.message);}
  finally{if(mounted.current)setBusy(false);}
 }
 return <div className="speech-controls">
  <p>Audio is sent to OpenAI for transcription. Temporary media is removed after processing. Up to 4 MB / two minutes. Review the transcript before using it.</p>
  <label className="speech-consent"><input type="checkbox" checked={consent} disabled={busy||recording||disabled} onChange={e=>setConsent(e.target.checked)}/> I agree to audio processing for transcription.</label>
  <div className="speech-actions"><button className="secondary" type="button" disabled={!consent||busy||disabled} onClick={record}>{recording?'Stop & transcribe':'Record a voice message'}</button>
  <label>Or upload audio/video <input type="file" accept=".wav,.mp3,.m4a,.mp4,.mov,.webm,.ogg,.mpeg,.mpga" disabled={!consent||busy||recording||disabled} onChange={e=>{cancelled.current=false;transcribe(e.target.files?.[0]);e.target.value='';}}/></label></div>
  {recording&&<p role="status">Recording… stops automatically before two minutes.</p>}{busy&&<p role="status">Preparing transcript…</p>}{error&&<p role="alert">{error}</p>}
 </div>;
}

export function MediaSource({language,disabled,onChange}){
 const [transcript,setTranscript]=useState(null),[confirmed,setConfirmed]=useState(false);
 function update(next,accepted=false){setTranscript(next);setConfirmed(accepted);onChange(accepted?next:null);}
 useEffect(()=>{onChange(null);},[]);
 return <div><SpeechInput language={language} disabled={disabled} onBegin={()=>update(null)} onTranscript={result=>update(result)}/>
 {transcript&&<div className="transcript-editor"><h3>Review the source transcript</h3><p>These segments become your source evidence. Correct words before confirming; timestamps refer to the original recording.</p>
 {transcript.segments.map((segment,index)=><label key={index}>{segment.start.toFixed(2)}s–{segment.end.toFixed(2)}s<textarea value={segment.text} maxLength={4000} disabled={disabled} onChange={e=>update({...transcript,segments:transcript.segments.map((s,i)=>i===index?{...s,text:e.target.value}:s)})}/></label>)}
 <label className="speech-consent"><input type="checkbox" checked={confirmed} disabled={disabled||transcript.segments.some(s=>!s.text.trim())} onChange={e=>update(transcript,e.target.checked)}/> I reviewed this transcript and want to use it as my source.</label></div>}
 </div>;
}

export function SpeechPlayback({sessionId,responseId,disabled}){
 const [url,setUrl]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const current=useRef(''),controller=useRef(null);
 useEffect(()=>()=>{controller.current?.abort();if(current.current)URL.revokeObjectURL(current.current);},[]);
 async function play(){
  setBusy(true);setError('');const abort=new AbortController();controller.current=abort;
  try{const response=await fetch('/api/sessions/'+sessionId+'/speech',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({response_id:responseId,consent:true}),signal:AbortSignal.any([abort.signal,AbortSignal.timeout(65000)])});if(!response.ok){const data=await response.json().catch(()=>({}));throw Error(data.detail||'Playback is unavailable.');}const blob=await response.blob();if(abort.signal.aborted)return;if(current.current)URL.revokeObjectURL(current.current);current.current=URL.createObjectURL(blob);setUrl(current.current);}
  catch(e){if(!abort.signal.aborted)setError(e.message);}
  finally{if(!abort.signal.aborted)setBusy(false);}
 }
 return <div className="speech-playback"><small>AI-generated voice. Playback sends this reply to OpenAI.</small>{url?<audio controls src={url} aria-label="AI-generated partner voice"/>:<button className="text-button" type="button" disabled={busy||disabled} onClick={play}>{busy?'Preparing voice…':'Play AI voice'}</button>}{error&&<small role="alert">{error}</small>}</div>;
}
