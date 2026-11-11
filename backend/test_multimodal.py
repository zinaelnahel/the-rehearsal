"""Offline contracts for speech consent, tool selection, tracing and persistence."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import wave

from fastapi import HTTPException
from fastapi.testclient import TestClient
from langchain_core.documents import Document
from langchain_core.messages import AIMessage
from langsmith.run_helpers import get_tracing_context
from backend import main as api, speech
from backend.agent import prepare
from backend.observability import synthetic_evaluation, trace_scope
from backend.retrieval import PersistentStore, build_store, database, purge_expired


class SpeechTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, {'VECTOR_STORE': 'memory', 'API_PROXY_TOKEN': '',
            'SPEECH_ENABLED': 'true', 'OPENAI_API_KEY': 'fictional-test-key',
            'REHEARSAL_AGENT_ENABLED': 'false'}))
        self.enterContext(patch.object(api, 'LIVE', False))
        self.client = self.enterContext(TestClient(api.app))

    def upload(self, consent='true', raw=b'fictional-audio'):
        return self.client.post('/api/speech/transcribe', files={'file': ('clip.webm', raw, 'audio/webm')},
            data={'language': 'German', 'consent': consent})

    def test_speech_uses_rehearsal_pronunciation_without_changing_text(self):
        for language, text, accent in (
            ('Spanish', '¿Cuánto cuesta el alquiler?', 'español de España'),
            ('German', 'Wie hoch ist die Miete?', 'Hochdeutsch'),
            ('English', 'How much is the rent?', 'Speak English'),
        ):
            with self.subTest(language=language), patch('backend.speech.speech_client') as client:
                client.return_value.audio.speech.create.return_value.content = b'mp3'
                reserve = Mock()
                self.assertEqual(speech.synthesize(text, reserve, language), b'mp3')
                reserve.assert_called_once_with()
                request = client.return_value.audio.speech.create.call_args.kwargs
                self.assertEqual(request['model'], 'gpt-4o-mini-tts')
                self.assertEqual(request['voice'], 'marin')
                self.assertEqual(request['input'], text)
                self.assertIn(accent, request['instructions'])

    def test_spoken_reply_omits_citations_but_preserves_job_numbers(self):
        text = 'El salario es de 30.000 euros en 13 pagas. [13] [14]'
        with patch('backend.speech.speech_client') as client:
            client.return_value.audio.speech.create.return_value.content = b'mp3'
            speech.synthesize(text, Mock(), 'Spanish')
            spoken = client.return_value.audio.speech.create.call_args.kwargs['input']
            self.assertEqual(spoken, 'El salario es de 30.000 euros en 13 pagas.')
            self.assertTrue(text.endswith('[13] [14]'))

    def test_citation_only_reply_does_not_request_speech(self):
        with patch('backend.speech.speech_client') as client:
            reserve = Mock()
            with self.assertRaises(HTTPException):
                speech.synthesize('[13] [14]', reserve, 'Spanish')
            reserve.assert_not_called()
            client.assert_not_called()

    def test_unknown_playback_language_never_calls_provider(self):
        with patch('backend.speech.speech_client') as client:
            reserve = Mock()
            with self.assertRaises(HTTPException):
                speech.synthesize('Hallo', reserve, 'untrusted-language')
            reserve.assert_not_called()
            client.assert_not_called()

    def test_consent_disabled_and_limits_prevent_provider_calls(self):
        with patch('backend.speech.speech_client') as provider:
            self.assertEqual(self.upload('false').status_code, 409)
            with patch.dict(os.environ, {'SPEECH_ENABLED': 'false'}):
                self.assertEqual(self.upload().status_code, 503)
            self.assertEqual(self.upload(raw=b'x' * (speech.MAX_BYTES + 65536)).status_code, 413)
            provider.assert_not_called()

    def test_transcript_requires_confirmation_and_preserves_timestamps(self):
        provider = Mock()
        provider.audio.transcriptions.create.return_value = SimpleNamespace(segments=[
            SimpleNamespace(start=1.2, end=3.4, text='Die Miete ist 1375 Euro.', no_speech_prob=0.01)])
        with patch('backend.speech.normalize_media', return_value=(b'wav', 4.0)), \
             patch('backend.speech.speech_client', return_value=provider):
            result = self.upload()
        self.assertEqual(result.status_code, 200, result.text)
        segments = result.json()['segments']
        self.assertEqual(self.client.post('/api/sessions', json={'transcript': segments}).status_code, 409)
        source = self.client.post('/api/sessions', json={'transcript': segments, 'transcript_confirmed': True})
        self.assertEqual(source.status_code, 200, source.text)
        sid = source.json()['id']
        docs = api.search(api.sessions[sid], 'Miete')
        self.assertEqual(docs[0].metadata['start'], 1.2)
        self.assertIn('1.20s', docs[0].metadata['location'])
        receipt = result.json()['audio_receipt']
        request = {'transcript': segments, 'transcript_confirmed': True, 'audio_receipt': receipt}
        audio = self.client.post('/api/sessions', json=request).json()
        state = api.sessions[audio['id']]
        self.assertTrue(state['uploaded_audio'])
        self.assertTrue(state['audio_timed'])
        passage = next(iter(state['source_chunks'].values()))
        view = self.client.get('/api/sessions/' + audio['id'] + '/source/' + passage.metadata['id']).json()
        self.assertTrue(view['browser_audio'])
        self.assertTrue(view['audio_timed'])
        for change in ({'text': 'Corrected words'}, {'start': 2.0}, {'end': 99.0}):
            edited = [{**segments[0], **change}]
            response = self.client.post('/api/sessions', json={**request, 'transcript': edited})
            self.assertEqual(response.status_code, 200, response.text)
            edited_state = api.sessions[response.json()['id']]
            self.assertFalse(edited_state['audio_timed'])
            self.assertTrue(all('start' not in d.metadata for d in edited_state['source_documents']))
        self.client.delete('/api/sessions/' + sid)

    def test_silence_and_provider_failure_do_not_create_sessions(self):
        provider = Mock()
        provider.audio.transcriptions.create.return_value = SimpleNamespace(segments=[
            SimpleNamespace(start=0, end=1, text='Hallucinated silence.', no_speech_prob=0.99)])
        with patch('backend.speech.normalize_media', return_value=(b'wav', 1.0)), \
             patch('backend.speech.speech_client', return_value=provider):
            self.assertEqual(self.upload().status_code, 400)
            provider.audio.transcriptions.create.side_effect = RuntimeError('fictional private provider error')
            result = self.upload()
            self.assertEqual(result.status_code, 502)
            self.assertNotIn('private provider error', result.text)
        self.assertFalse(api.sessions)

    def test_unclear_segments_are_rejected_without_creating_a_source(self):
        provider=Mock()
        for quality in ({'avg_logprob':-2.0},{'compression_ratio':3.0}):
            provider.audio.transcriptions.create.return_value=SimpleNamespace(segments=[
                SimpleNamespace(start=0,end=1,text='Uncertain synthetic words',no_speech_prob=0,**quality)])
            with patch('backend.speech.normalize_media',return_value=(b'wav',1.0)), patch('backend.speech.speech_client',return_value=provider):
                self.assertEqual(self.upload().status_code,400)
        self.assertFalse(api.sessions)

    def test_decoder_rejects_long_media_and_removes_temporary_files(self):
        paths = []
        def decode(args, **kwargs):
            paths.append(Path(args[-1]).parent)
            with wave.open(args[-1], 'wb') as wav:
                wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(16000)
                wav.writeframes(b'\0\0' * 16000 * 121)
            return SimpleNamespace(returncode=0)
        with patch('backend.speech.shutil.which', return_value='ffmpeg'), \
             patch('backend.speech.subprocess.run', side_effect=decode):
            with self.assertRaises(HTTPException) as error:
                speech.normalize_media(b'clip', 'clip.mp4')
        self.assertEqual(error.exception.status_code, 400)
        self.assertFalse(paths[0].exists())

    def test_playback_uses_only_session_owned_assistant_text(self):
        ids = []
        for _ in range(2):
            sid = self.client.post('/api/sessions', json={'text': 'Monthly rent is 850 euros.'}).json()['id']
            ids.append(sid)
            self.client.post(f'/api/sessions/{sid}/mission', json={'scenario': 'apartment'})
            self.client.post(f'/api/sessions/{sid}/start', json={'goals': ['Ask the rent']})
        reply = api.sessions[ids[0]]['turns'][0]
        with patch('backend.speech.synthesize', return_value=b'fictional-mp3') as provider:
            body = {'response_id': reply['id'], 'consent': True}
            self.assertEqual(self.client.post(f'/api/sessions/{ids[1]}/speech', json=body).status_code, 404)
            self.assertEqual(self.client.post(f'/api/sessions/{ids[0]}/speech', json={**body, 'text': 'injected'}).status_code, 422)
            result = self.client.post(f'/api/sessions/{ids[0]}/speech', json=body)
            self.assertEqual(result.content, b'fictional-mp3')
            self.assertEqual(result.headers['content-type'], 'audio/mpeg')
            self.assertEqual(provider.call_args.args[0], reply['content'])
            self.assertEqual(provider.call_args.args[2], api.sessions[ids[0]]['setup']['language'])
        for sid in ids:
            self.client.delete('/api/sessions/' + sid)


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.session = {'setup': {'language': 'English'}, 'turns': [], 'mission': [
            {'id': '0', 'text': 'Ask the rent', 'achieved': False}]}
        self.doc = Document(page_content='Rent is 1375 euros.', metadata={'id': '1',
            'location': 'Section 1', 'source': 'fictional'})

    def call(self, name, arguments, identifier='call-1'):
        return AIMessage(content='', tool_calls=[{'name': name, 'args': arguments, 'id': identifier}])

    def test_model_selects_different_tools_and_cannot_commit_goals(self):
        selections = []
        for name, arguments in [('retrieve_evidence', {'query': 'rent'}), ('inspect_goal_progress', {}),
                                ('get_practice_hint', {}), ('check_evidence', {'source_id': '1', 'quote': 'Rent is 1375 euros.'})]:
            with self.subTest(name=name):
                model = Mock(side_effect=[self.call(name, arguments), AIMessage(content='Ready')])
                search = Mock(return_value=[self.doc])
                selected, docs = prepare(self.session, 'Fictional turn', [self.doc], model, search, api.evidence)
                selections.append(selected[0]['tool'])
                self.assertFalse(self.session['mission'][0]['achieved'])
                self.assertEqual(docs[0].page_content, 'Rent is 1375 euros.')
        self.assertEqual(len(set(selections)), 4)

    def test_unknown_tool_cross_session_arguments_and_budget_are_rejected(self):
        variants = [self.call('shell', {}), self.call('retrieve_evidence', {'query': 'rent', 'sid': 'another-session'}),
            AIMessage(content='', tool_calls=[{'name': 'inspect_goal_progress', 'args': {}, 'id': str(i)} for i in range(5)])]
        for response in variants:
            with self.subTest(response=response):
                with self.assertRaises(HTTPException):
                    prepare(self.session, 'rent', [self.doc], Mock(return_value=response), Mock(), api.evidence)

    def test_repeated_tool_requests_stop_after_two_model_calls(self):
        invoke = Mock(return_value=self.call('inspect_goal_progress', {}))
        calls, _ = prepare(self.session, 'goals', [self.doc], invoke, Mock(), api.evidence)
        self.assertEqual(invoke.call_count, 2)
        self.assertEqual(len(calls), 2)

    def test_agent_cannot_bypass_required_evidence_review(self):
        with patch.dict(os.environ, {'VECTOR_STORE': 'memory', 'API_PROXY_TOKEN': '', 'REHEARSAL_AGENT_ENABLED': 'true'}), \
             patch.object(api, 'LIVE', False), TestClient(api.app) as client:
            sid = client.post('/api/sessions', json={'text': 'Rent is 1375 euros.'}).json()['id']
            path = '/api/sessions/' + sid
            client.post(path + '/mission', json={'scenario': 'apartment'})
            client.post(path + '/start', json={'goals': ['Ask the rent']})
            from backend.live import RoleReply, EvidenceReview
            proposal = RoleReply(reply='The rent is one euro.', citations=[], goal_checks=[], answer_checks=[])
            review = EvidenceReview(partner_role_consistent=True,reply_supported=False, accepted_goal_ids=[], verified_answer_goal_ids=[])
            with patch.object(api, 'LIVE', True), patch.object(api, 'agent_model', return_value=AIMessage(content='Skip checks')), \
                 patch.object(api, 'model', side_effect=[proposal, review]) as calls:
                result = client.post(path + '/turn', json={'text': 'What is the rent?'})
            self.assertEqual(result.status_code, 200, result.text)
            self.assertTrue(result.json()['turn']['answer_withheld'])
            self.assertEqual(calls.call_count, 2)
            client.delete(path)


class PersistenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Chroma holds open SQLite handles on Windows. Keep its test directory
        # inside ignored runtime rather than attempting to remove open files.
        root = Path(__file__).resolve().parents[1] / '.runtime'
        root.mkdir(exist_ok=True)
        cls.path = tempfile.mkdtemp(prefix='chroma-test-', dir=root)

    def setUp(self):
        self.enterContext(patch.dict(os.environ, {'VECTOR_STORE': 'chroma', 'CHROMA_PATH': self.path,
                                               'API_PROXY_TOKEN': ''}))
        self.document = Document(page_content='Rent is 1375 euros.', metadata={
            'id': '1', 'source': 'fictional', 'location': 'Section 1'})

    def test_restart_isolation_and_expiry(self):
        a = build_store('session-a', api.LocalEmbeddings(), [self.document])
        b = build_store('session-b', api.LocalEmbeddings(), [Document(page_content='Rent is 900 euros.',
            metadata={'id': '1', 'source': 'other', 'location': 'Section 1'})])
        self.addCleanup(b.delete)
        # A fresh Python process must read from disk, not this client's memory.
        code = ('from backend.retrieval import PersistentStore; from backend.main import LocalEmbeddings; '
                's=PersistentStore("session-a",LocalEmbeddings()); '
                'assert s.similarity_search("rent")[0].page_content == "Rent is 1375 euros."')
        result = subprocess.run([sys.executable, '-c', code], capture_output=True, timeout=40)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
        self.assertNotIn('1375', b.similarity_search('rent')[0].page_content)
        a.touch()
        a.collection.modify(metadata={'embedding': 'local-hash-512-v1', 'expires_at': 0})
        purge_expired()
        with self.assertRaises(Exception):
            PersistentStore('session-a', api.LocalEmbeddings())
        self.assertEqual(b.similarity_search('rent')[0].metadata['id'], '1')

    def test_delete_after_restart_removes_collection(self):
        store = build_store('restart-deletion', api.LocalEmbeddings(), [self.document])
        with TestClient(api.app) as client:
            result = client.delete('/api/sessions/restart-deletion')
            self.assertEqual(result.status_code, 200)
        names = [entry if isinstance(entry, str) else entry.name for entry in database().list_collections()]
        self.assertNotIn(store.name, names)


class MediaDecoderTests(unittest.TestCase):
    def test_selected_clip_decodes_only_requested_interval(self):
        raw = io.BytesIO()
        with wave.open(raw, 'wb') as wav:
            wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(16000)
            wav.writeframes(b'\0\0' * 16000 * 4)
        audio, duration = speech.normalize_media(raw.getvalue(), 'recording.wav', clip_start=2, clip_seconds=1)
        self.assertTrue(audio.startswith(b'RIFF'))
        self.assertAlmostEqual(duration, 1, delta=0.1)

    def test_real_ffmpeg_decodes_audio_and_video_without_provider_calls(self):
        import imageio_ffmpeg
        executable = imageio_ffmpeg.get_ffmpeg_exe()
        with tempfile.TemporaryDirectory(prefix='rehearsal-decoder-test-') as folder:
            audio = Path(folder) / 'sample.wav'
            with wave.open(str(audio), 'wb') as wav:
                wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(16000)
                wav.writeframes(b'\0\0' * 16000)
            video = Path(folder) / 'sample.mp4'
            result = subprocess.run([executable, '-nostdin', '-hide_banner', '-loglevel', 'error',
                '-f', 'lavfi', '-i', 'color=c=black:s=64x64:d=1', '-i', str(audio),
                '-shortest', '-c:v', 'mpeg4', '-c:a', 'aac', '-y', str(video)],
                capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
            with patch('backend.speech.speech_client') as provider:
                formats=[audio,video]
                for suffix,codec in [('mp3','libmp3lame'),('m4a','aac'),('ogg','libvorbis'),('webm','libopus'),('mov','aac')]:
                    target=Path(folder)/('sample.'+suffix)
                    encoded=subprocess.run([executable,'-nostdin','-hide_banner','-loglevel','error',
                        '-i',str(audio),'-c:a',codec,'-y',str(target)],capture_output=True,timeout=20)
                    self.assertEqual(encoded.returncode,0,encoded.stderr.decode(errors='replace'))
                    formats.append(target)
                for media in formats:
                    normalized, duration = speech.normalize_media(media.read_bytes(), media.name)
                    self.assertTrue(normalized.startswith(b'RIFF'))
                    self.assertAlmostEqual(duration, 1, delta=0.1)
                no_audio=Path(folder)/'no-audio.mp4'
                encoded=subprocess.run([executable,'-nostdin','-hide_banner','-loglevel','error',
                    '-f','lavfi','-i','color=c=black:s=64x64:d=1','-an','-c:v','mpeg4','-y',str(no_audio)],capture_output=True,timeout=20)
                self.assertEqual(encoded.returncode,0)
                for raw,name in [(no_audio.read_bytes(),no_audio.name),(b'invalid media','broken.wav')]:
                    with self.assertRaises(HTTPException) as caught:
                        speech.normalize_media(raw,name)
                    self.assertEqual(caught.exception.status_code,400)
                provider.assert_not_called()


class LangSmithRunnerTests(unittest.TestCase):
    def test_fixed_synthetic_dataset_upload_and_failed_metric_exit(self):
        from scripts import evaluate_langsmith as runner
        from uuid import uuid4
        client = Mock()
        client.has_dataset.return_value = False
        client.create_dataset.return_value = SimpleNamespace(id=uuid4())
        cases = json.loads((runner.ROOT / 'evaluation/rag-dataset.json').read_text(encoding='utf-8'))
        class Experiment(list):
            experiment_name = 'fictional-offline-test'
        rows = Experiment([{'run': SimpleNamespace(id=uuid4(), outputs={'passed': True, 'checks': {'fictional': True}}),
            'evaluation_results': {'results': [SimpleNamespace(score=0 if i == 0 else 1, key='deterministic_checks')]}}
            for i in range(len(cases))])
        with tempfile.TemporaryDirectory(prefix='rehearsal-evaluation-test-') as folder, \
             patch.dict(os.environ, {'LANGSMITH_API_KEY': 'fictional-not-a-key'}), \
             patch.object(sys, 'argv', ['evaluate_langsmith.py', '--output', str(Path(folder) / 'report.json')]), \
             patch.object(runner, 'Client', return_value=client), patch.object(runner, 'evaluate', return_value=rows) as evaluate:
            self.assertEqual(runner.main(), 1)
            self.assertEqual(client.create_examples.call_args.kwargs['inputs'], cases)
            self.assertEqual(evaluate.call_args.kwargs['max_concurrency'], 1)
            self.assertIn('source_sha256', evaluate.call_args.kwargs['metadata'])


class TraceBoundaryTests(unittest.TestCase):
    def test_environment_and_headers_cannot_enable_user_tracing(self):
        with patch.dict(os.environ, {'LANGSMITH_TRACING': 'true'}), trace_scope():
            self.assertFalse(get_tracing_context()['enabled'])
        with synthetic_evaluation(), trace_scope():
            self.assertTrue(get_tracing_context()['enabled'])
        with trace_scope():
            self.assertFalse(get_tracing_context()['enabled'])


if __name__ == '__main__':
    unittest.main()
