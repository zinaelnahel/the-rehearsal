"""Explicit paid synthetic TTS -> audio/video -> Whisper API round-trip check.

Uses only fictional scripted openings. Does not measure human microphone accuracy.
Temporary media is deleted; the report contains only synthetic text and metrics.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import unicodedata
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fastapi.testclient import TestClient
from backend import main as api


def words(text):
    normalized = ''.join(c for c in unicodedata.normalize('NFD', text.casefold())
                         if unicodedata.category(c) != 'Mn')
    return re.findall(r'\w+', normalized)


def word_error_rate(reference, transcript):
    expected, actual = words(reference), words(transcript)
    previous = list(range(len(actual) + 1))
    for index, word in enumerate(expected, 1):
        current = [index]
        for position, candidate in enumerate(actual, 1):
            current.append(min(current[-1] + 1, previous[position] + 1,
                               previous[position - 1] + (word != candidate)))
        previous = current
    return previous[-1] / max(1, len(expected))


def require(response):
    if response.status_code != 200:
        raise RuntimeError(f'API returned HTTP {response.status_code}')
    return response.json()


def case(client, language):
    identifiers = []
    row = {'language': language, 'input_kind': 'video' if language == 'German' else 'audio', 'passed': False}
    try:
        sid = require(client.post('/api/sessions', json={'text': 'Monthly rent is 850 euros.'}))['id']
        identifiers.append(sid)
        path = '/api/sessions/' + sid
        require(client.post(path + '/mission', json={'scenario': 'apartment', 'language': language,
            'feedback_language': 'English', 'level': 'Everyday'}))
        started = require(client.post(path + '/start', json={'goals': ['Ask about the apartment']}))
        reply = started['turns'][0]
        row['reference'] = reply['content']
        before = time.monotonic()
        playback = client.post(path + '/speech', json={'response_id': reply['id'], 'consent': True})
        if playback.status_code != 200 or not playback.headers.get('content-type', '').startswith('audio/mpeg'):
            raise RuntimeError(f'Playback returned HTTP {playback.status_code}')
        row['tts_seconds'] = round(time.monotonic() - before, 3)
        media, filename, content_type = playback.content, 'synthetic.mp3', 'audio/mpeg'
        if language == 'German':
            import imageio_ffmpeg
            with tempfile.TemporaryDirectory(prefix='rehearsal-speech-eval-') as folder:
                source, target = Path(folder) / 'voice.mp3', Path(folder) / 'video.mp4'
                source.write_bytes(media)
                result = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-nostdin', '-hide_banner',
                    '-loglevel', 'error', '-f', 'lavfi', '-i', 'color=c=black:s=64x64:r=10',
                    '-i', str(source), '-shortest', '-c:v', 'mpeg4', '-c:a', 'aac', '-y', str(target)],
                    capture_output=True, timeout=20)
                if result.returncode:
                    raise RuntimeError('Synthetic video preparation failed')
                media, filename, content_type = target.read_bytes(), 'synthetic.mp4', 'video/mp4'
        before = time.monotonic()
        transcript = require(client.post('/api/speech/transcribe',
            files={'file': (filename, media, content_type)}, data={'language': language, 'consent': 'true'}))
        row['stt_seconds'] = round(time.monotonic() - before, 3)
        row['transcript'] = transcript['text']
        row['duration_seconds'] = transcript['duration']
        row['normalized_word_error_rate'] = round(word_error_rate(reply['content'], transcript['text']), 4)
        reviewed = require(client.post('/api/sessions', json={'transcript': transcript['segments'],
                                                             'transcript_confirmed': True}))
        identifiers.append(reviewed['id'])
        documents = api.search(api.sessions[reviewed['id']], transcript['text'])
        row['timestamped_source_ingestion'] = bool(documents and 'start' in documents[0].metadata)
        row['passed'] = (row['normalized_word_error_rate'] <= 0.25 and row['timestamped_source_ingestion']
                         and bool(transcript['segments']))
    except Exception as error:
        row['error_type'] = type(error).__name__
    finally:
        row['deletion_verified'] = True
        for identifier in identifiers:
            deleted = client.delete('/api/sessions/' + identifier)
            row['deletion_verified'] &= deleted.status_code == 200 and client.get(
                '/api/sessions/' + identifier + '/status').status_code == 404
        row['passed'] &= row['deletion_verified']
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / '.runtime/speech-evaluation.json')
    args = parser.parse_args()
    if not os.getenv('OPENAI_API_KEY'):
        parser.error('OPENAI_API_KEY is required; this makes six paid speech calls.')
    report = {'run_at_utc': datetime.now(timezone.utc).isoformat(), 'tts_model': api.speech.TTS_MODEL,
        'stt_model': 'whisper-1', 'fixture_type': 'TTS-generated scripted fictional openings',
        'limitation': 'Three synthetic round trips; not human-recorded speech, microphone usability or broad accuracy.',
        'word_error_gate': 0.25, 'cases': [], 'passed': False,
        'source_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                          for name in ('backend/main.py', 'backend/speech.py', 'scripts/evaluate_speech.py')}}
    before = len(api.model_calls)
    with patch.object(api, 'LIVE', False), patch.dict(os.environ, {'SPEECH_ENABLED': 'true',
            'API_PROXY_TOKEN': '', 'LANGSMITH_TRACING': 'false', 'LANGCHAIN_TRACING_V2': 'false'}), TestClient(api.app) as client:
        for language in ('English', 'German', 'Spanish'):
            row = case(client, language)
            report['cases'].append(row)
            print(language, 'PASS' if row['passed'] else 'FAIL', flush=True)
    report['provider_calls'] = len(api.model_calls) - before
    report['passed'] = all(row['passed'] for row in report['cases'])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Report:', args.output)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
