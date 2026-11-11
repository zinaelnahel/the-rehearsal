'use client';
import {useEffect,useRef,useState} from 'react';
import {useI18n} from './i18n';
import script from '../samples/audio/family-boundary.es.json';

export default function AudioSample({disabled,onChange}){
 const {t}=useI18n();
 const player=useRef(null);
 const [text,setText]=useState(()=>script.turns.map(turn=>turn.speaker+': '+turn.text).join('\n\n'));
 const [confirmed,setConfirmed]=useState(false),[audioError,setAudioError]=useState(false);
 useEffect(()=>{onChange(null);return()=>onChange(null);},[onChange]);
 useEffect(()=>{if(disabled)player.current?.pause();},[disabled]);
 function confirm(value){
  setConfirmed(value);
  onChange(value?{source_method:'scripted_sample_audio',transcript_text:text}:null);
 }
 return <div className="transcript-editor">
  <h3>{t(script.title)}</h3>
  <p>{t('Fictional Spanish voice message with an AI-generated voice. A family member has already counted on your help without asking first.')}</p>
  <audio ref={player} controls preload="none" src="/api/samples/difficult/audio" aria-label={t('Boundary-setting audio sample')} onError={()=>setAudioError(true)}/>
  {audioError&&<p role="status">{t('Audio could not be played. You can still review the script below and practise the conversation.')}</p>}
  <p>{t('You reply to the message and set your own boundary. The AI plays the sender. You can refuse, ask about the plans, or offer another time.')}</p>
  <p className="subtle">{t('This is one boundary-setting example. For a breakup, a conversation with a friend, or another difficult situation, choose Your situation and describe your own context.')}</p>
  <label htmlFor="sample-audio-transcript">{t('Review the audio transcript')}</label>
  <textarea id="sample-audio-transcript" rows={10} value={text} maxLength={100000} disabled={disabled} onChange={event=>{setText(event.target.value);setConfirmed(false);onChange(null);}}/>
  <p className="subtle">{t('Keep the transcript unchanged for playable timestamped citations. If you edit the words, citations refer to text sections instead.')}</p>
  <label className="speech-consent"><input type="checkbox" checked={confirmed} disabled={disabled||!text.trim()} onChange={event=>confirm(event.target.checked)}/> {t('I reviewed this audio transcript and want to use it for my rehearsal.')}</label>
 </div>;
}
