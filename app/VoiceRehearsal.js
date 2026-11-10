'use client';
import {forwardRef,useEffect,useImperativeHandle,useRef,useState} from 'react';
import {useI18n} from './i18n';
import {VoiceSession} from './voice-session';
import {LoadingClapper} from './LoadingCue';

const statusLabels={
  idle:'Voice mode is off.',starting:'Connecting your microphone…',
  listening:'Listening. Take your time.',hearing:'Your turn. Pause when you are finished.',
  transcribing:'Transcribing your turn…',thinking:'Checking the reply against your sources…',
  preparing:'Preparing your partner’s voice…',speaking:'Your partner is speaking.',muted:'Microphone muted.'
};

const VoiceRehearsal=forwardRef(function VoiceRehearsal({sessionId,language,responseId,disabled,onTurn,onTranscript,onActiveChange},ref){
  const {t,errorText}=useI18n();
  const [consent,setConsent]=useState(false);
  const [snapshot,setSnapshot]=useState({state:'idle',active:false,muted:false});
  const [error,setError]=useState('');
  const [elapsed,setElapsed]=useState(0);
  const waiting=['transcribing','thinking','preparing'].includes(snapshot.state);
  useEffect(()=>{
    setElapsed(0);
    if(!waiting)return;
    const started=Date.now();
    const timer=setInterval(()=>setElapsed(Math.floor((Date.now()-started)/1000)),1000);
    return()=>clearInterval(timer);
  },[snapshot.state,waiting]);
  const engine=useRef(null);
  const handlers=useRef({onTurn,onTranscript,onActiveChange});
  handlers.current={onTurn,onTranscript,onActiveChange};
  useImperativeHandle(ref,()=>({stop:()=>engine.current?.stop()}),[]);

  useEffect(()=>{
    let mounted=true;
    const session=new VoiceSession({sessionId,language,
      onTurn:text=>handlers.current.onTurn(text),
      onTranscript:text=>handlers.current.onTranscript(text),
      onChange:next=>{if(mounted){setSnapshot(next);handlers.current.onActiveChange(next.active);}},
      onError:message=>{if(mounted)setError(message);}
    });
    engine.current=session;
    const hide=()=>{if(document.hidden)session.stop();};
    const leave=()=>session.stop();
    document.addEventListener('visibilitychange',hide);
    window.addEventListener('pagehide',leave);
    return()=>{
      mounted=false;
      session.stop();
      if(engine.current===session)engine.current=null;
      handlers.current.onActiveChange(false);
      document.removeEventListener('visibilitychange',hide);
      window.removeEventListener('pagehide',leave);
    };
  },[sessionId,language]);

  return <details className="voice-rehearsal" onToggle={event=>{if(!event.currentTarget.open)engine.current?.stop();}}><summary>{t('Rehearse out loud')}</summary><section aria-label={t('Voice rehearsal')}>
    <div className="voice-heading"><span className={'voice-indicator '+(snapshot.active?'active':'')} aria-hidden="true"/></div>
    <p className="subtle">{t('Speak, pause, and hear your partner reply. Replies are checked before they are spoken. Use headphones to reduce echo.')}</p>
    {!snapshot.active&&<>
      <label className="speech-consent"><input type="checkbox" checked={consent} disabled={disabled} onChange={event=>setConsent(event.target.checked)}/>{t('I agree to send microphone audio and partner replies to OpenAI. Voice transcripts are sent automatically as my messages; I can read them in the conversation.')}</label>
    </>}
    <div className="voice-actions">{snapshot.active?<>
      <button className="secondary" type="button" aria-pressed={snapshot.muted} onClick={()=>engine.current?.toggleMute()}>{snapshot.muted?t('Unmute microphone'):t('Mute microphone')}</button>
      {snapshot.state==='hearing'&&<button className="secondary" type="button" onClick={()=>engine.current?.submitRecording?.()}>{t('Send voice turn now')}</button>}
      {['preparing','speaking'].includes(snapshot.state)&&<button className="secondary" type="button" onClick={()=>engine.current?.interrupt()}>{t('Interrupt & speak')}</button>}
      <button className="text-button" type="button" onClick={()=>engine.current?.stop()}>{t('Stop voice mode')}</button>
    </>:<button className="secondary" type="button" disabled={!consent||disabled} onClick={()=>{setError('');void engine.current.start(responseId);}}>{t('Start voice rehearsal')}</button>}</div>
    <p className="voice-status" role="status">{t(statusLabels[snapshot.state])}</p>
    {waiting&&<div className="voice-wait"><LoadingClapper/><div><p>{t('Time in this step: {seconds} seconds.').replace('{seconds}',elapsed)}</p><ol aria-label={t('Voice reply progress')}>
      {['transcribing','thinking','preparing'].map((stage,index)=><li key={stage} aria-current={snapshot.state===stage?'step':undefined}>{t(['Transcribe your words','Check the reply','Prepare the voice'][index])}</li>)}
    </ol>{elapsed>=8&&<p>{t('Voice works in separate steps, so replies can take a while. You can stop voice mode and continue with text.')}</p>}</div></div>}
    {snapshot.active&&<small>{t('Your microphone pauses during replies. Interrupt to take your turn. Stopping voice mode does not undo a message already sent.')}</small>}
    {error&&<p role="alert">{errorText(error)}</p>}
  </section></details>;
});

export default VoiceRehearsal;
