'use client';
import {useEffect,useState} from 'react';
import {useI18n} from './i18n';
import transcript from '../samples/apartment-transcript.es.json';
import {videoTime} from './video-evidence.mjs';

export default function VideoSample({disabled,onChange}){
 const {t}=useI18n();
 const [text,setText]=useState(()=>transcript.segments.map(s=>s.text).join('\n\n'));
 const [confirmed,setConfirmed]=useState(false);
 useEffect(()=>{onChange(null);return()=>onChange(null);},[onChange]);
 return <div className="transcript-editor">
  <p><a href={transcript.source_url} target="_blank" rel="noreferrer">{t('Watch the flat viewing')} ↗</a></p>
  <p>{t('Prepared Spanish captions from the video. Automatic captions may contain errors; watch the video and review before using them. No caption import is needed.')}</p>
  <details><summary>{t('Check captions with video timestamps')}</summary><ol>{transcript.segments.map((segment,index)=><li key={index}><a href={transcript.source_url+'&t='+Math.floor(segment.start)} target="_blank" rel="noreferrer">{videoTime(segment.start)}–{videoTime(segment.end)}</a> {segment.text}</li>)}</ol></details>
  <label htmlFor="sample-video-transcript">{t('Review the video transcript')}</label>
  <textarea id="sample-video-transcript" rows={12} maxLength={100000} value={text} disabled={disabled} onChange={e=>{setText(e.target.value);setConfirmed(false);onChange(null);}}/>
  <p className="subtle">{t('Unchanged text links evidence to approximate video timestamps. Edited text uses text sections instead. The video stays in Spanish in every conversation language.')}</p>
  <label className="speech-consent"><input type="checkbox" checked={confirmed} disabled={disabled||!text.trim()} onChange={e=>{setConfirmed(e.target.checked);onChange(e.target.checked?{source_method:'prepared_sample_video',sample_video_text:text}:null);}}/> {t('I reviewed this transcript and want to use it as my source.')}</label>
 </div>;
}
