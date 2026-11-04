"""Video-link import contracts, without requests to external video providers."""
import io
import os
import socket
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient
from backend import main as api, video


class VideoTests(unittest.TestCase):
    def test_pasted_transcript_requires_confirmation_and_preserves_honest_provenance(self):
        body={'transcript_text':'Monthly rent is 1375 euros. Pets are not allowed.',
              'video_url':'https://www.youtube.com/watch?v=abcdefghijk'}
        self.assertEqual(self.client.post('/api/sessions',json=body).status_code,409)
        with patch('backend.video.read_public') as reader,patch('backend.main.model') as model:
            response=self.client.post('/api/sessions',json={**body,'transcript_confirmed':True})
            self.assertEqual(response.status_code,200,response.text)
            reader.assert_not_called();model.assert_not_called()
        data=response.json();sid=data['id']
        try:
            self.assertEqual(data['import_method'],'pasted_transcript')
            evidence=api.evidence(api.search(api.sessions[sid],'rent')[0])
            self.assertIn('not fetched',evidence['source'])
            self.assertNotIn('timestamp',evidence['location'])
            self.assertEqual(evidence['url'],body['video_url'])
        finally:self.client.delete('/api/sessions/'+sid)
        for changes in ({'transcript_text':' '},{'text':'Mixed source'},{'video_url':'http://127.0.0.1/private'}):
            self.assertEqual(self.client.post('/api/sessions',json={**body,'transcript_confirmed':True,**changes}).status_code,400)

    def test_youtube_http_block_reports_server_rejection_without_response_body(self):
        response=Mock(status=429)
        connection=Mock();connection.getresponse.return_value=response
        with patch('backend.video.public_address',return_value='8.8.8.8'),patch('backend.video.PinnedHTTPS',return_value=connection):
            with self.assertRaises(HTTPException) as caught:
                video.read_public('https://www.youtube.com/api/timedtext',100,time.monotonic()+10,allowed_hosts=video.YOUTUBE)
        self.assertEqual(caught.exception.status_code,424)
        self.assertIn('HTTP 429',caught.exception.detail)
        self.assertIn('may still play in your browser',caught.exception.detail)
        connection.close.assert_called_once()

    def setUp(self):
        self.enterContext(patch.dict(os.environ, {'VECTOR_STORE': 'memory', 'API_PROXY_TOKEN': '',
            'SPEECH_ENABLED': 'true', 'OPENAI_API_KEY': 'fictional-key'}))
        self.enterContext(patch.object(api, 'LIVE', False))
        self.client = self.enterContext(TestClient(api.app))
        api.video_imports.clear()

    def test_youtube_variants_and_url_validation(self):
        for value in ['https://youtu.be/abcdefghijk?t=15', 'https://www.youtube.com/watch?v=abcdefghijk',
                      'https://youtube.com/shorts/abcdefghijk', 'https://m.youtube.com/embed/abcdefghijk']:
            self.assertEqual(video.youtube_id(value), 'abcdefghijk')
        for value in ['http://example.com/clip.mp4', 'https://127.0.0.1/video.mp4',
                      'https://user:secret@example.com/a.mp4', 'https://example.com:8443/clip.mp4',
                      'https://youtube.com/playlist?list=example', 'https://youtube.com/watch?v=bad',
                      'https://example.com/a\r\nInjected: header']:
            with self.subTest(value=value), self.assertRaises(HTTPException):
                video.youtube_id(value)
        self.assertEqual(video.reference_url('https://cdn.example.com/video.mp4?signature=secret'),
                         'https://cdn.example.com/video.mp4')

    def test_private_or_mixed_dns_is_rejected(self):
        for addresses in [['127.0.0.1'], ['10.1.2.3'], ['169.254.169.254'], ['8.8.8.8', '192.168.0.1']]:
            records = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (address, 443)) for address in addresses]
            with patch('backend.video.socket.getaddrinfo', return_value=records), self.assertRaises(HTTPException):
                video.public_address('cdn.example.com')

    def test_tls_connection_pins_validated_ip_and_checks_original_hostname(self):
        connection = video.PinnedHTTPS('cdn.example.com', '8.8.8.8', 8)
        raw_socket = Mock()
        tls_context = Mock()
        connection._context = tls_context
        with patch('backend.video.socket.create_connection', return_value=raw_socket) as connect:
            connection.connect()
        self.assertEqual(connect.call_args.args[0], ('8.8.8.8', 443))
        tls_context.wrap_socket.assert_called_once_with(raw_socket, server_hostname='cdn.example.com')

    def test_redirects_revalidate_destination_before_connecting(self):
        response = Mock(status=302)
        response.getheader.side_effect = lambda name, default=None: 'https://private.example.com/a.mp4' if name == 'Location' else default
        connection = Mock()
        connection.getresponse.return_value = response
        with patch('backend.video.public_address', side_effect=['8.8.8.8', HTTPException(400, 'Private address')]), \
             patch('backend.video.PinnedHTTPS', return_value=connection) as connect, self.assertRaises(HTTPException):
            video.read_public('https://cdn.example.com/a.mp4', 100, time.monotonic() + 10)
        self.assertEqual(connect.call_count, 1)
        connection.close.assert_called_once()

    def test_streamed_payload_is_bounded_without_content_length(self):
        response = Mock(status=200)
        response.getheader.side_effect = lambda name, default=None: default
        response.read1.side_effect = io.BytesIO(b'x' * 101).read
        connection = Mock()
        connection.getresponse.return_value = response
        with patch('backend.video.public_address', return_value='8.8.8.8'), \
             patch('backend.video.PinnedHTTPS', return_value=connection), self.assertRaises(HTTPException) as error:
            video.read_public('https://cdn.example.com/a.mp4', 100, time.monotonic() + 10)
        self.assertEqual(error.exception.status_code, 413)

    def test_direct_video_uses_whisper_but_web_pages_do_not(self):
        transcript = {'segments': [{'start': 0, 'end': 2, 'text': 'Rent is 1420 euros.'}]}
        with patch('backend.video.read_public', return_value=(b'fictional-video', {'Content-Type': 'video/mp4'},
                'https://cdn.example.com/a.mp4?signature=secret')), \
             patch('backend.video.speech.transcribe', return_value=transcript) as transcribe:
            result = video.import_video('https://cdn.example.com/a.mp4', 'English', Mock())
        self.assertEqual(result['source_method'], 'linked_video_whisper')
        self.assertNotIn('secret', result['source_url'])
        self.assertEqual(transcribe.call_args.args[0], b'fictional-video')
        with patch('backend.video.read_public', return_value=(b'page', {'Content-Type': 'text/html'},
                'https://example.com/watch')), patch('backend.video.speech.transcribe') as transcribe:
            with self.assertRaises(HTTPException) as error:
                video.import_video('https://example.com/watch', 'English', Mock())
            self.assertEqual(error.exception.status_code, 422)
            transcribe.assert_not_called()

    def test_caption_excerpt_is_reviewed_and_cited_with_original_url(self):
        class Captions(list):
            is_generated = True
        captions = Captions([SimpleNamespace(start=0, duration=2, text='Rent is 1420 euros.'),
                             SimpleNamespace(start=130, duration=5, text='Outside the excerpt.')])
        with patch('youtube_transcript_api.YouTubeTranscriptApi.fetch', return_value=captions):
            preview = self.client.post('/api/video/transcript', json={
                'url': 'https://youtu.be/abcdefghijk', 'language': 'English', 'consent': True})
        self.assertEqual(preview.status_code, 200, preview.text)
        data = preview.json()
        self.assertEqual(len(data['segments']), 2)
        self.assertEqual(data['segments'][1]['start'], 130)
        self.assertIn('Outside the excerpt.', data['segments'][1]['text'])
        self.assertFalse(api.sessions)
        self.assertEqual(self.client.post('/api/sessions', json={'transcript': data['segments'],
            'video_url': data['source_url']}).status_code, 409)
        source = self.client.post('/api/sessions', json={'transcript': data['segments'],
            'video_url': data['source_url'], 'transcript_confirmed': True})
        sid = source.json()['id']
        evidence = api.evidence(api.search(api.sessions[sid], 'rent')[0])
        self.assertEqual(evidence['url'], 'https://www.youtube.com/watch?v=abcdefghijk')
        self.assertEqual(evidence['start'], 0)
        self.client.delete('/api/sessions/' + sid)

    def test_consent_errors_and_import_budget(self):
        body = {'url': 'https://youtu.be/abcdefghijk', 'language': 'English'}
        with patch('backend.main.import_video') as importer:
            self.assertEqual(self.client.post('/api/video/transcript', json=body).status_code, 409)
            importer.assert_not_called()
        with patch('youtube_transcript_api.YouTubeTranscriptApi.fetch', side_effect=RuntimeError('private error')):
            response = self.client.post('/api/video/transcript', json={**body, 'consent': True})
            self.assertEqual(response.status_code, 424)
            self.assertNotIn('private error', response.text)
        api.video_imports.extend([time.monotonic()] * 60)
        self.assertEqual(self.client.post('/api/video/transcript', json={**body, 'consent': True}).status_code, 429)

    def test_full_caption_text_limit_rejects_without_silent_truncation(self):
        snippets = [SimpleNamespace(start=i*31, duration=2, text='x'*3999) for i in range(30)]
        with self.assertRaises(HTTPException) as error:
            video.caption_segments(snippets)
        self.assertEqual(error.exception.status_code, 413)
        self.assertIn('100,000', error.exception.detail)
        segments = video.caption_segments([SimpleNamespace(start=3600, duration=3, text='Late information.')])
        self.assertEqual(segments[0]['start'], 3600)

    def test_direct_clip_offsets_timestamps_and_source_accepts_late_evidence(self):
        transcript = {'segments': [{'start': 1, 'end': 2, 'text': 'The price is 1420 euros.'}]}
        with patch('backend.video.read_public', return_value=(b'video', {'Content-Type': 'video/mp4'}, 'https://example.com/a.mp4')), \
             patch('backend.video.speech.transcribe', return_value=transcript) as transcribe:
            result = video.import_video('https://example.com/a.mp4', 'English', Mock(), 180, 30)
        self.assertEqual(transcribe.call_args.args[-2:], (180, 30))
        self.assertEqual(result['segments'][0]['start'], 181)
        self.assertEqual(result['segments'][0]['end'], 182)
        source = self.client.post('/api/sessions', json={'transcript': result['segments'],
            'transcript_confirmed': True, 'video_url': result['source_url']})
        self.assertEqual(source.status_code, 200, source.text)
        self.client.delete('/api/sessions/' + source.json()['id'])
        with patch('backend.main.import_video') as importer:
            response = self.client.post('/api/video/transcript', json={'url': 'https://example.com/a.mp4',
                'consent': True, 'clip_start': 180, 'clip_seconds': 121})
            self.assertEqual(response.status_code, 422)
            importer.assert_not_called()


if __name__ == '__main__':
    unittest.main()
