# Media navigation and upload verification — 9 November 2026

The source editor now stays mounted in a hidden container when navigating to
the plan, rehearsal or review. Video URL, media mode, edited timestamp blocks
and review confirmation remain in tab memory. Hidden recording controls are
disabled, and focus moves to the visible step heading. End-and-delete remounts
the source form and clears the draft; page reloads do not preserve it. Editing
the source still requires review/confirmation before rebuilding a mission.

Audio/video uploads now read file bytes before constructing the multipart
request, matching document-upload handling. An unreadable browser file handle
fails locally with a reselect-file message. Oversized files fail before a request;
cancelling while reading a file prevents it from being sent. No automatic upload
retry was added. Both microphone modes explain that a missing device requires
connecting a microphone, uploading a recording, or typing instead.

## Verification

- Node regression tests cover byte snapshots, filename/type/language/consent,
  unreadable files, size limits, cancellation and missing-device errors.
- Chrome verified video import, editing, confirmation, source/plan navigation,
  rebuilding without another import, and clearing after deletion.
- A synthetic one-second PCM WAV went through the real browser multipart request,
  local Next proxy, FastAPI and FFmpeg. Only the provider response was stubbed.
  The returned audio transcript and confirmation also survived navigation.

This does not establish the cause of the reported hosted network failure,
successful real-provider transcription on this revision, or physical-device
microphone capture. No paid provider calls or real recordings were used.

## Reproduce locally

Install the locked Python dependencies, Node dependencies and Playwright. Start
`python scripts/media_test_backend.py` in one terminal; it binds only to loopback
and substitutes a synthetic speech provider. Do not use it for public hosting.

Build the frontend, then start it in another PowerShell terminal:

```powershell
$env:BACKEND_URL='http://127.0.0.1:8031'
$env:API_PROXY_TOKEN=''
npm run build
npm run start -- --hostname 127.0.0.1 --port 3031
```

Run `npm run test:media` and `node scripts/test_media_browser.mjs`. Set
`CHROME_PATH` for a system Chrome installation if Playwright has no bundled
browser. The browser harness refuses non-local target URLs; other API responses
are mocked so mission generation makes no provider calls.
