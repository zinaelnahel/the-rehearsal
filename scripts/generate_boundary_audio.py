"""Explicit one-off generation of the fictional Spanish sample; uses paid TTS.

No learner data is sent. The generated WAV is bundled for playback without API
calls. Keep credentials in the local environment or ignored .env, never output.
"""
import io
import hashlib
import json
from pathlib import Path
import sys
import wave

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
 from dotenv import load_dotenv
 from openai import OpenAI
 from backend import budget
 load_dotenv(ROOT/'.env')
 script=json.loads((ROOT/'samples/audio/family-boundary.es.json').read_text(encoding='utf-8'))
 client=OpenAI(timeout=45,max_retries=0)
 frames=[]
 elapsed=0
 params=None
 for index,turn in enumerate(script['turns']):
  budget.reserve()
  response=client.audio.speech.create(model='gpt-4o-mini-tts',voice=turn['voice'],
   input=turn['text'],response_format='wav',instructions=
   'Habla en español de España, con claridad y un ritmo conversacional tranquilo, adecuado para estudiantes de nivel B1-B2. '
   'Interpreta una conversación cotidiana y respetuosa entre familiares. No exageres las emociones. '
   'Lee únicamente el texto proporcionado, sin añadir ni omitir palabras.')
  with wave.open(io.BytesIO(response.content)) as audio:
   current=(audio.getnchannels(),audio.getsampwidth(),audio.getframerate())
   if params is None:params=current
   if params!=current:raise ValueError('TTS audio formats do not match.')
   # The provider's streaming WAV header can contain an unknown-length sentinel.
   # Measure the decoded PCM bytes, never the declared frame count.
   pcm=audio.readframes(audio.getnframes())
   duration=len(pcm)/(audio.getframerate()*audio.getnchannels()*audio.getsampwidth())
   turn.update(start=round(elapsed,4),end=round(elapsed+duration,4))
   frames.append(pcm)
   frames.append(b'\x00'*int(params[2]*0.4)*params[0]*params[1])
   elapsed+=duration+0.4
  print(f'Generated line {index+1}/{len(script["turns"])}',flush=True)
 target=ROOT/'samples/audio/family-boundary.es.wav'
 with wave.open(str(target),'wb') as output:
  output.setnchannels(params[0]);output.setsampwidth(params[1]);output.setframerate(params[2])
  output.writeframes(b''.join(frames))
 with wave.open(str(target),'rb') as audio:
  duration=audio.getnframes()/audio.getframerate()
 if duration>120 or target.stat().st_size>4*1024*1024:
  raise ValueError('Generated sample exceeds audio limits.')
 script.update(audio_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),duration=duration)
 (ROOT/'samples/audio/family-boundary.es.json').write_text(json.dumps(script,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(f'Saved fictional audio: {duration:.1f} seconds; {target.stat().st_size} bytes')


if __name__=='__main__':
 try:main()
 except Exception as exc:
  print('Audio generation failed: '+type(exc).__name__,file=sys.stderr)
  raise SystemExit(1) from None
