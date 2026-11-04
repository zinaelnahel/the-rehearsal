"""Public video-link import: bounded direct media or available YouTube captions."""
import http.client
import ipaddress
import re
import socket
import ssl
import time
from pathlib import PurePosixPath
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit, urlunsplit

from fastapi import HTTPException
from pydantic import Field
import requests
from backend import speech

FALLBACK = 'Try another public link, paste the transcript in this panel, or upload a short audio/video file.'
YOUTUBE = {'youtube.com', 'www.youtube.com', 'm.youtube.com', 'youtu.be', 'www.youtu.be'}
MAX_TRANSCRIPT_CHARS = 100000


class SourceSegment(speech.Segment):
    """Source timestamps can cover a full video, unlike bounded speech recordings."""
    start: float = Field(ge=0, allow_inf_nan=False)
    end: float = Field(ge=0, allow_inf_nan=False)


def caption_segments(fetched):
    segments = []
    characters = 0
    previous_start = -1
    for snippet in fetched:
        text = snippet.text.strip()
        if not text:
            continue
        item = SourceSegment(start=snippet.start, end=snippet.start + snippet.duration, text=text)
        if item.start < previous_start:
            raise HTTPException(422, 'The caption timestamps are not ordered. ' + FALLBACK)
        previous_start = item.start
        characters += len(text) + 1
        if characters > MAX_TRANSCRIPT_CHARS:
            raise HTTPException(413, 'The full transcript exceeds 100,000 characters. Use a shorter video or paste a selected excerpt.')
        # Group short caption lines into reviewable timestamped paragraphs.
        if segments and item.start - segments[-1]['start'] <= 30 and len(segments[-1]['text']) + len(text) + 1 <= 4000:
            segments[-1]['text'] += ' ' + text
            segments[-1]['end'] = max(segments[-1]['end'], item.end)
        else:
            segments.append(item.model_dump())
        if len(segments) > 1000:
            raise HTTPException(413, 'The transcript has too many timestamp blocks. Use a shorter video or selected excerpt.')
    return segments


def public_url(value):
    try:
        if any(c.isspace() or ord(c) < 32 for c in value):
            raise ValueError()
        parts = urlsplit(value)
        host = (parts.hostname or '').encode('idna').decode('ascii').lower()
        if parts.scheme != 'https' or parts.username or parts.password or parts.port not in (None, 443):
            raise ValueError()
        if not re.fullmatch(r'(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}', host):
            raise ValueError()
        return urlunsplit(('https', host, parts.path or '/', parts.query, ''))
    except (ValueError, UnicodeError, TypeError):
        raise HTTPException(400, 'Use a public HTTPS video link without a login, custom port or IP address.') from None


def youtube_id(value):
    url = public_url(value)
    parts = urlsplit(url)
    if parts.hostname not in YOUTUBE:
        return None
    if parts.hostname in ('youtu.be', 'www.youtu.be'):
        identifier = parts.path.strip('/')
    elif parts.path == '/watch':
        values = parse_qs(parts.query).get('v', [])
        identifier = values[0] if len(values) == 1 else ''
    else:
        match = re.fullmatch(r'/(?:shorts|embed|live)/([\w-]{11})/?', parts.path, re.ASCII)
        identifier = match.group(1) if match else ''
    if not re.fullmatch(r'[A-Za-z0-9_-]{11}', identifier):
        raise HTTPException(400, 'Use a link to one YouTube video, not a channel or playlist.')
    return identifier


def reference_url(value):
    identifier = youtube_id(value)
    if identifier:
        return 'https://www.youtube.com/watch?' + urlencode({'v': identifier})
    parts = urlsplit(public_url(value))
    # Do not send signed query parameters into model context or retain them.
    return urlunsplit((parts.scheme, parts.netloc, parts.path, '', ''))


def public_address(host):
    try:
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
            raise ValueError()
        return addresses[0][4][0]
    except (OSError, ValueError):
        raise HTTPException(400, 'The video address must resolve only to public internet addresses.') from None


class PinnedHTTPS(http.client.HTTPSConnection):
    """TLS uses the original hostname; TCP uses the already-validated address."""
    def __init__(self, host, address, timeout):
        super().__init__(host, timeout=timeout, context=ssl.create_default_context())
        self.address = address

    def connect(self):
        connection = socket.create_connection((self.address, 443), timeout=self.timeout)
        try:
            self.sock = self._context.wrap_socket(connection, server_hostname=self.host)
        except Exception:
            connection.close()
            raise


def read_public(url, limit, deadline, method='GET', body=None, headers=None, allowed_hosts=None):
    for _ in range(4):
        url = public_url(url)
        parts = urlsplit(url)
        if allowed_hosts and parts.hostname not in allowed_hosts:
            raise HTTPException(424, 'The caption provider redirected outside its supported hosts. ' + FALLBACK)
        address = public_address(parts.hostname)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise HTTPException(504, 'Video import timed out. ' + FALLBACK)
        connection = PinnedHTTPS(parts.hostname, address, min(8, remaining))
        try:
            target = urlunsplit(('', '', parts.path, parts.query, ''))
            safe_headers = {'User-Agent': 'TheRehearsal/0.7', 'Accept-Encoding': 'identity'}
            safe_headers.update(headers or {})
            # Never forward a Host, proxy credential or authorization header.
            safe_headers = {k: v for k, v in safe_headers.items()
                            if k.lower() not in ('host', 'authorization', 'proxy-authorization')}
            safe_headers = {k: v for k, v in safe_headers.items() if k.lower() != 'accept-encoding'}
            safe_headers['Accept-Encoding'] = 'identity'
            connection.request(method, target, body=body, headers=safe_headers)
            response = connection.getresponse()
            if response.status in (301, 302, 303, 307, 308):
                if method != 'GET':
                    raise HTTPException(424, 'The caption provider redirected its request. ' + FALLBACK)
                url = urljoin(url, response.getheader('Location', ''))
                continue
            if response.status != 200:
                if allowed_hosts and parts.hostname in YOUTUBE:
                    message=(f'YouTube rejected this server’s caption request (HTTP {response.status}). The video may still play in your browser. '
                             if response.status in (403,429) else f'YouTube returned HTTP {response.status} while reading captions. ')
                    raise HTTPException(424,message+'Paste the transcript in this panel, or upload a short audio/video file. No transcript was imported.')
                raise HTTPException(424, 'The provider blocked this read or the video is unavailable. ' + FALLBACK)
            if response.getheader('Content-Encoding', 'identity').lower() not in ('', 'identity'):
                raise HTTPException(424, 'The provider returned an unsupported compressed response. ' + FALLBACK)
            length = response.getheader('Content-Length')
            if length and (not length.isdigit() or int(length) > limit):
                raise HTTPException(413, 'The linked content is too large. Direct videos must be at most 4 MB.')
            chunks = bytearray()
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise HTTPException(504, 'Video import timed out. ' + FALLBACK)
                connection.sock.settimeout(min(8, remaining)) if connection.sock else None
                chunk = response.read1(min(65536, limit + 1 - len(chunks)))
                if not chunk:
                    break
                chunks.extend(chunk)
                if len(chunks) > limit:
                    raise HTTPException(413, 'The linked content is too large. Direct videos must be at most 4 MB.')
            return bytes(chunks), dict(response.getheaders()), url
        finally:
            connection.close()
    raise HTTPException(424, 'The video redirected too many times. ' + FALLBACK)


class CaptionSession(requests.Session):
    """Caption SDK HTTP calls use the same pinned, bounded public-only reader."""
    def __init__(self, deadline):
        super().__init__()
        self.trust_env = False
        self.deadline = deadline
        self.calls = 0

    def request(self, method, url, **kwargs):
        self.calls += 1
        if self.calls > 8 or method.upper() not in ('GET', 'POST'):
            raise HTTPException(424, 'Caption import exceeded its request budget. ' + FALLBACK)
        prepared = self.prepare_request(requests.Request(method, url,
            params=kwargs.get('params'), headers=kwargs.get('headers'),
            data=kwargs.get('data'), json=kwargs.get('json')))
        raw, headers, final_url = read_public(prepared.url, 2 * 1024 * 1024, self.deadline,
            method=method.upper(), body=prepared.body, headers=prepared.headers,
            allowed_hosts={'www.youtube.com', 'youtube.com'})
        response = requests.Response()
        response.status_code = 200
        response._content = raw
        response.headers.update(headers)
        response.encoding = 'utf-8'
        response.url = final_url
        response.request = prepared
        return response


def import_video(value, language, reserve, clip_start=None, clip_seconds=120):
    if language not in speech.CODES:
        raise HTTPException(400, 'Choose English, German or Spanish.')
    url = public_url(value)
    identifier = youtube_id(url)
    deadline = time.monotonic() + (25 if identifier else 12)
    try:
        if identifier:
            from youtube_transcript_api import YouTubeTranscriptApi
            with CaptionSession(deadline) as session:
                fetched = YouTubeTranscriptApi(http_client=session).fetch(identifier,
                    languages=[speech.CODES[language]])
            segments = caption_segments(fetched)
            if not segments:
                raise HTTPException(422, 'No readable captions were found. ' + FALLBACK)
            return {'segments': segments, 'language': language, 'source_url': reference_url(url),
                'source_method': 'youtube_captions', 'is_generated': fetched.is_generated,
                'requires_confirmation': True,
                'notice': 'Full available transcript imported. YouTube captions may contain errors; review before use.'}
        speech.require_speech(True)
        raw, headers, final_url = read_public(url, speech.MAX_BYTES, deadline)
        content_type = next((v for k, v in headers.items() if k.lower() == 'content-type'), '').split(';')[0].lower()
        suffix = {'video/mp4': '.mp4', 'video/webm': '.webm', 'video/quicktime': '.mov'}.get(content_type)
        if content_type == 'application/octet-stream':
            candidate = PurePosixPath(urlsplit(final_url).path).suffix.lower()
            suffix = candidate if candidate in ('.mp4', '.webm', '.mov') else None
        if not suffix:
            raise HTTPException(422, 'This link returns a web page or unsupported media. Use a direct MP4, WebM or MOV file URL, or a YouTube video link. ' + FALLBACK)
        result = (speech.transcribe(raw, 'linked-video' + suffix, language, reserve) if clip_start is None else
                  speech.transcribe(raw, 'linked-video' + suffix, language, reserve, clip_start, clip_seconds))
        if clip_start is not None:
            result['segments'] = [{**segment, 'start': segment['start'] + clip_start,
                                   'end': segment['end'] + clip_start} for segment in result['segments']]
        return {**result, 'source_url': reference_url(final_url), 'source_method': 'linked_video_whisper',
                'notice': ('Selected clip transcribed by Whisper; timestamps refer to the original video. ' if clip_start is not None else 'Audio transcribed by Whisper. ') + 'Review before use. Signed URL query parameters are not retained.'}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(424, 'The video or captions could not be imported. Captions may be unavailable in the selected language, or the provider may block automated reads. ' + FALLBACK) from None
