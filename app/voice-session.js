import {api} from './api-client.js';

const MAX_BYTES=4*1024*1024;
const MAX_RECORDING_MS=90000;
const IDLE_MS=30000;

// Half-duplex audio: only validated, server-stored partner replies are spoken.
// A generation token prevents stopped/obsolete work from restarting the mic.
export class VoiceSession {
  constructor({sessionId,language,onTurn,onTranscript,onChange,onError}) {
    Object.assign(this,{sessionId,language,onTurn,onTranscript,onChange,onError});
    this.active=false;
    this.muted=false;
    this.generation=0;
    this.silenceMs=1200;
    this.state='idle';
  }

  update(state=this.state) {
    this.state=state;
    this.onChange({state,active:this.active,muted:this.muted});
  }

  current(token) { return this.active&&token===this.generation; }

  async start(responseId) {
    if(this.active)return;
    this.active=true;
    this.muted=false;
    const token=++this.generation;
    this.update('starting');
    try {
      const AudioContext=window.AudioContext||window.webkitAudioContext;
      if(!navigator.mediaDevices?.getUserMedia||!window.MediaRecorder||!AudioContext) {
        throw Error('Continuous voice is unavailable in this browser. Type your message instead.');
      }
      this.mime=['audio/webm','audio/mp4','audio/ogg'].find(type=>MediaRecorder.isTypeSupported(type));
      if(!this.mime)throw Error('This browser cannot record a supported audio format. Upload a file instead.');
      this.context=new AudioContext();
      await this.context.resume();
      if(!this.current(token))return;
      const stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:true}});
      if(!this.current(token)){stream.getTracks().forEach(track=>track.stop());return;}
      this.stream=stream;
      stream.getAudioTracks().forEach(track=>{
        track.onended=()=>{if(this.current(token))this.fail(Error('The microphone disconnected. Check your device and start voice mode again.'),token);};
      });
      this.source=this.context.createMediaStreamSource(stream);
      this.analyser=this.context.createAnalyser();
      this.analyser.fftSize=2048;
      this.source.connect(this.analyser);
      this.samples=new Float32Array(this.analyser.fftSize);
      this.microphone(false);
      if(responseId)await this.speak(responseId,token);
      else this.listen(token);
    } catch(error) { this.fail(error,token); }
  }

  microphone(enabled) {
    this.stream?.getAudioTracks().forEach(track=>{track.enabled=enabled;});
  }

  discardRecording() {
    clearInterval(this.poll);
    this.poll=null;
    const recorder=this.recorder;
    this.recorder=null;
    if(recorder){
      recorder.onstop=null;
      recorder.ondataavailable=null;
      recorder.onerror=null;
      if(recorder.state!=='inactive')recorder.stop();
    }
    this.microphone(false);
  }

  listen(token) {
    if(!this.current(token))return;
    try { this.beginRecording(token); }
    catch(error) { this.fail(error,token); }
  }

  beginRecording(token) {
    if(!this.current(token))return;
    if(this.muted){this.update('muted');return;}
    this.discardRecording();
    this.microphone(true);
    const recorder=new MediaRecorder(this.stream,{mimeType:this.mime,audioBitsPerSecond:64000});
    this.recorder=recorder;
    const chunks=[];
    let bytes=0,started=performance.now(),lastVoice=started,voiceMs=0,previous=started;
    let heard=false,submitted=false;
    recorder.ondataavailable=event=>{
      if(!this.current(token)||!event.data.size)return;
      bytes+=event.data.size;
      if(bytes>MAX_BYTES){this.fail(Error('Recording exceeded 4 MB. Try a shorter recording.'),token);return;}
      chunks.push(event.data);
    };
    recorder.onerror=()=>this.fail(Error('Microphone recording failed. Try uploading a file or type instead.'),token);
    recorder.onstop=()=>{
      if(!this.current(token)||!submitted)return;
      this.recorder=null;
      const type=this.mime;
      const extension=type.includes('mp4')?'m4a':type.includes('ogg')?'ogg':'webm';
      void this.process(new File(chunks,'voice-turn.'+extension,{type}),token);
    };
    const submit=()=>{
      if(submitted||!this.current(token))return;
      submitted=true;
      clearInterval(this.poll);
      this.poll=null;
      this.microphone(false);
      this.update('transcribing');
      recorder.stop();
    };
    this.submitRecording=()=>{if(heard)submit();};
    recorder.start(250);
    this.update('listening');
    this.poll=setInterval(()=>{
      if(!this.current(token))return;
      if(this.context.state!=='running'){
        this.fail(Error('Voice mode was paused by the browser. Return to this tab and start again.'),token);return;
      }
      const now=performance.now();
      this.analyser.getFloatTimeDomainData(this.samples);
      const rms=Math.sqrt(this.samples.reduce((sum,value)=>sum+value*value,0)/this.samples.length);
      if(rms>0.015){
        voiceMs+=Math.min(now-previous,100);
        lastVoice=now;
        if(!heard&&voiceMs>=250){heard=true;this.update('hearing');}
      } else if(!heard&&now-lastVoice>150)voiceMs=0;
      previous=now;
      if(heard&&now-lastVoice>=this.silenceMs)submit();
      else if(now-started>=MAX_RECORDING_MS&&heard)submit();
      else if(!heard&&now-started>=IDLE_MS)this.fail(Error('No speech was detected. Voice mode stopped; start again when you are ready.'),token);
    },50);
  }

  async process(file,token) {
    const controller=new AbortController();
    this.request=controller;
    try {
      const form=new FormData();
      form.append('file',file,file.name);
      form.append('language',this.language);
      form.append('consent','true');
      const transcript=await api('/speech/transcribe',form,'POST',controller.signal);
      if(!this.current(token))return;
      const text=transcript.text?.trim();
      if(!text)throw Error('No clear speech was detected. Try a clearer recording or type your text.');
      this.onTranscript(text);
      if(text.length>2000)throw Error('Your voice turn is too long. Review and shorten the transcript below, then send it as text.');
      this.request=null;
      this.update('thinking');
      // Do not abort or retry a submitted turn: it may already be committed.
      // The parent still reconciles the response if voice mode is stopped.
      const result=await this.onTurn(text);
      if(!this.current(token))return;
      if(result.safety){this.stop();return;}
      await this.speak(result.turn.id,token);
    } catch(error) { this.fail(error,token); }
    finally { if(this.request===controller)this.request=null; }
  }

  clearPlayback() {
    this.playRequest?.abort();
    this.playRequest=null;
    if(this.audio){
      this.audio.onended=null;
      this.audio.onerror=null;
      this.audio.pause();
      this.audio.removeAttribute('src');
      this.audio.load();
      this.audio=null;
    }
    if(this.audioUrl){URL.revokeObjectURL(this.audioUrl);this.audioUrl=null;}
  }

  async speak(responseId,token) {
    if(!this.current(token))return;
    const controller=new AbortController();
    this.playRequest=controller;
    this.update('preparing');
    try {
      const response=await fetch('/api/sessions/'+this.sessionId+'/speech',{
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({response_id:responseId,consent:true}),
        signal:AbortSignal.any([controller.signal,AbortSignal.timeout(65000)])
      });
      if(!response.ok){
        const data=await response.json().catch(()=>({}));
        throw Error(typeof data.detail==='string'?data.detail:'Speech playback could not be generated. The text reply is still available.');
      }
      const blob=await response.blob();
      if(!this.current(token)||controller.signal.aborted)return;
      this.audioUrl=URL.createObjectURL(blob);
      const audio=new Audio(this.audioUrl);
      this.audio=audio;
      audio.onended=()=>{
        if(!this.current(token)||this.audio!==audio)return;
        this.clearPlayback();
        this.listen(token);
      };
      audio.onerror=()=>{if(this.audio===audio)this.fail(Error('Voice playback failed. Your partner reply is still available as text.'),token);};
      await audio.play();
      if(this.current(token)&&this.audio===audio)this.update('speaking');
    } catch(error) {
      if(!controller.signal.aborted)this.fail(error.name==='NotAllowedError'
        ? Error('Your browser blocked automatic audio. Allow sound for this site, then start voice mode again.'):error,token);
    }
  }

  interrupt() {
    if(!this.active||!['speaking','preparing'].includes(this.state))return;
    this.clearPlayback();
    this.muted=false;
    this.listen(this.generation);
  }

  toggleMute() {
    if(!this.active)return;
    this.muted=!this.muted;
    if(this.muted&&['listening','hearing'].includes(this.state)){
      this.discardRecording();
      this.update('muted');
    } else if(!this.muted&&this.state==='muted')this.listen(this.generation);
    else this.update();
  }

  fail(error,token) {
    if(!this.current(token))return;
    this.stop();
    this.onError(error.name==='NotAllowedError'
      ? 'Microphone permission was denied. Upload a recording or type instead.'
      :error.message||'Voice mode stopped. Check your connection and try again.');
  }

  stop() {
    this.active=false;
    this.generation++;
    this.discardRecording();
    this.submitRecording=null;
    this.request?.abort();
    this.request=null;
    this.clearPlayback();
    this.stream?.getTracks().forEach(track=>{track.onended=null;track.stop();});
    this.stream=null;
    this.source?.disconnect();
    this.source=null;
    void this.context?.close().catch(()=>{});
    this.context=null;
    this.muted=false;
    this.update('idle');
  }
}
