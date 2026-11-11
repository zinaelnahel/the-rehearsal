"""Bounded audio/video decoding and explicit provider speech calls."""
import io
import math
import os
import re
from pathlib import Path
import shutil
import subprocess
import tempfile
import wave

from fastapi import HTTPException
from pydantic import BaseModel, Field, model_validator

MAX_BYTES = 4 * 1024 * 1024
MAX_SECONDS = 120
EXTENSIONS = {'.wav', '.mp3', '.mp4', '.m4a', '.webm', '.ogg', '.mpeg', '.mpga', '.mov'}
DEMUXERS = {'.wav': 'wav', '.mp3': 'mp3', '.mp4': 'mov', '.m4a': 'mov',
            '.mov': 'mov', '.webm': 'matroska', '.ogg': 'ogg', '.mpeg': 'mpeg', '.mpga': 'mp3'}
CODES = {'English': 'en', 'German': 'de', 'Spanish': 'es'}
TTS_MODEL = 'gpt-4o-mini-tts'
TTS_VOICE = 'marin'
PRONUNCIATION = {
    'English': 'Speak English with natural, clear pronunciation.',
    'Spanish': 'Habla en español de España, con pronunciación castellana estándar y distinción entre s y z o c ante e/i. Usa una entonación natural de España.',
    'German': 'Sprich auf Standarddeutsch (Hochdeutsch), mit natürlicher deutscher Aussprache und Intonation, ohne regionalen Dialekt.',
}


class Segment(BaseModel):
    model_config = {'extra': 'forbid'}
    start: float = Field(ge=0, le=MAX_SECONDS, allow_inf_nan=False)
    end: float = Field(ge=0, le=MAX_SECONDS, allow_inf_nan=False)
    text: str = Field(min_length=1, max_length=4000)

    @model_validator(mode='after')
    def ordered(self):
        if self.end < self.start or not self.text.strip():
            raise ValueError('Use nonempty transcript segments with ordered timestamps.')
        return self


def enabled():
    return os.getenv('SPEECH_ENABLED', 'false').lower() == 'true'


def require_speech(consent):
    if not enabled():
        raise HTTPException(503, 'Speech is disabled on this server. Use text or ask the operator to enable speech.')
    if not consent:
        raise HTTPException(409, 'Review the audio processing notice and agree before using speech.')
    if not os.getenv('OPENAI_API_KEY'):
        raise HTTPException(503, 'Speech requires a provider key on the server.')


def normalize_media(raw, filename, clip_start=None, clip_seconds=MAX_SECONDS):
    if clip_start is not None and (not math.isfinite(clip_start) or not 0 <= clip_start <= 86400
                                  or not math.isfinite(clip_seconds) or not 1 <= clip_seconds <= MAX_SECONDS):
        raise HTTPException(400, 'Choose a valid clip start and a duration between 1 and 120 seconds.')
    suffix = Path(filename).suffix.lower()
    if suffix not in EXTENSIONS:
        raise HTTPException(400, 'Choose WAV, MP3, M4A, MP4, MOV, WebM, OGG or MPEG media.')
    if not raw or len(raw) > MAX_BYTES:
        raise HTTPException(413, 'Choose a nonempty media file up to 4 MB.')
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        try:
            import imageio_ffmpeg
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        except (ImportError, RuntimeError):
            pass
    if not ffmpeg:
        raise HTTPException(503, 'Speech decoding requires FFmpeg on the server. Text rehearsal is available.')
    # Local paths only, no URLs/playlists, no stdin, one thread, bounded output.
    # TemporaryDirectory cleans on success and exceptions, including timeouts.
    try:
        with tempfile.TemporaryDirectory(prefix='rehearsal-media-') as folder:
            source = Path(folder) / ('input' + suffix)
            target = Path(folder) / 'audio.wav'
            source.write_bytes(raw)
            seek = ['-ss', str(clip_start)] if clip_start is not None else []
            result = subprocess.run([ffmpeg, '-nostdin', '-hide_banner', '-loglevel', 'error',
                '-protocol_whitelist', 'file,pipe', '-f', DEMUXERS[suffix], '-threads', '1', *seek, '-i', str(source),
                '-map', '0:a:0', '-vn', '-t', str(clip_seconds if clip_start is not None else MAX_SECONDS + 1), '-ac', '1', '-ar', '16000',
                '-c:a', 'pcm_s16le', '-threads', '1', '-y', str(target)],
                capture_output=True, timeout=15, check=False)
            if result.returncode or not target.exists():
                raise HTTPException(400, 'Could not decode audio. Choose a valid media file with an audio track.')
            audio = target.read_bytes()
    except subprocess.TimeoutExpired:
        raise HTTPException(400, 'Media decoding took too long. Choose a shorter recording.') from None
    try:
        with wave.open(io.BytesIO(audio)) as wav:
            duration = wav.getnframes() / wav.getframerate()
    except (wave.Error, ZeroDivisionError):
        raise HTTPException(400, 'The audio track could not be read.') from None
    if duration > MAX_SECONDS or duration < 0.1:
        raise HTTPException(400, 'Record between 0.1 seconds and two minutes of speech.')
    return audio, duration


def speech_client():
    from openai import OpenAI
    return OpenAI(timeout=25, max_retries=0)


def transcribe(raw, filename, language, reserve, clip_start=None, clip_seconds=MAX_SECONDS):
    if language not in CODES:
        raise HTTPException(400, 'Choose English, German or Spanish.')
    audio, duration = (normalize_media(raw, filename) if clip_start is None else
                       normalize_media(raw, filename, clip_start, clip_seconds))
    reserve()
    try:
        result = speech_client().audio.transcriptions.create(model='whisper-1',
            file=('audio.wav', audio, 'audio/wav'), language=CODES[language],
            response_format='verbose_json', timestamp_granularities=['segment'])
        segments = []
        for item in result.segments or []:
            # Whisper can hallucinate on silence. Reject high no-speech segments;
            # learner confirmation remains required even for accepted segments.
            if (getattr(item, 'no_speech_prob', 0) > 0.6
                    or getattr(item, 'avg_logprob', 0) < -1.0
                    or getattr(item, 'compression_ratio', 0) > 2.4):
                continue
            start, end = float(item.start), float(item.end)
            if not math.isfinite(start) or not math.isfinite(end):
                continue
            start, end = max(0, min(start, duration)), max(0, min(end, duration))
            if item.text.strip() and end >= start:
                segments.append(Segment(start=start, end=end, text=item.text.strip()).model_dump())
        if not segments:
            raise HTTPException(400, 'No clear speech was detected. Try a clearer recording or type your text.')
        if len(segments) > 200 or sum(len(s['text']) for s in segments) > 100000:
            raise HTTPException(400, 'The transcript is too large.')
        return {'segments': segments, 'duration': duration, 'language': language,
                'text': ' '.join(s['text'] for s in segments), 'requires_confirmation': True}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(502, 'Transcription failed. Retry or use text; no transcript was saved.') from None


def synthesize(text, reserve, language):
    if language not in PRONUNCIATION:
        raise HTTPException(400, 'Choose English, German or Spanish.')
    if not text.strip() or len(text) > 4000:
        raise HTTPException(400, 'This reply is too long for speech playback.')
    # Evidence markers belong in the chat, not in spoken dialogue. Preserve
    # ordinary numbers such as salaries, hours and dates.
    text = re.sub(r'\s+', ' ', re.sub(r'\[\d+\]', '', text)).strip()
    text = re.sub(r'\s+([,.;:!?])', r'\1', text)
    if not text:
        raise HTTPException(400, 'This reply has no spoken text.')
    reserve()
    try:
        result = speech_client().audio.speech.create(model=TTS_MODEL, voice=TTS_VOICE,
            input=text, response_format='mp3', instructions=PRONUNCIATION[language] +
            ' Read only the supplied text, preserving its words and meaning. Use a natural conversational pace and clear articulation. Do not add commentary or read these instructions aloud.')
        return result.content
    except Exception:
        raise HTTPException(502, 'Speech playback could not be generated. The text reply is still available.') from None
