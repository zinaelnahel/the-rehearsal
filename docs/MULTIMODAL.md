# Multimodal implementation and activation

The source now implements Whisper transcription, optional TTS, a bounded
LangChain tool-calling agent, a LangSmith experiment runner and persistent Chroma
retrieval. Current real-provider speech, agent, browser and hosted LangSmith
results are linked in [SUBMISSION.md](../SUBMISSION.md). Release-specific hosting
checks are recorded on the GitHub v0.7.0 release. Free hosting uses memory
retrieval; persistent Chroma is a local demonstration.

## Run locally

Install the updated `backend/requirements.txt` and start the backend/frontend as
described in README. FFmpeg is installed in Docker; local installs can use the
binary bundled by `imageio-ffmpeg` when FFmpeg is not on PATH.

```dotenv
REHEARSAL_MODE=live
OPENAI_API_KEY=your-server-key
SPEECH_ENABLED=true
REHEARSAL_AGENT_ENABLED=true
VECTOR_STORE=chroma
CHROMA_PATH=.runtime/chroma
```

Keep real keys in ignored local environment files. Restart the backend after
changes. `GET /api/config` reports speech, agent and vector store capabilities.
Speech can be enabled independently of demo chat, and makes external provider
calls even when chat uses the offline demo. Speech controls are hidden when disabled.

## Speech workflow

- Select **Audio / video** as source, choose **Record or upload audio / video**, agree to audio processing, record or upload,
  correct each timestamped segment and confirm it before building a mission.
- The rehearsal offers continuous voice or the text composer. Turns are limited
  to 2,000 characters. The duplicate manual record/upload control was removed
  from the conversation; media sources still have their own review workflow.
- Alternatively, select **Start voice rehearsal** after accepting its separate
  notice. This mode automatically submits recognized speech as learner messages,
  runs the existing retrieval/generation/evidence-review pipeline, and plays only
  the stored, validated partner reply. It first reads the current partner turn.
  The transcript, citations and goal updates remain visible in the conversation.
  No unchecked generated text is streamed to the user.
- Browser-local volume detection ends a turn after a short 1.2-second pause;
  **Send voice turn now** also ends a detected turn.
  This is volume-based detection, not semantic turn detection. Background noise
  can cause false starts, and quiet speech can be missed. Use headphones to
  reduce echo. Capture is capped at 90 seconds/4 MB;
  30 seconds without detected speech stops voice mode without a provider call.
- The microphone is disabled while transcribing, validating and playing audio.
  **Interrupt & speak** cancels playback/preparation and starts listening;
  automatic spoken interruption is not implemented. **Mute microphone** discards
  an unsent recording; **Stop voice mode** releases the device and cancels pending
  transcription/playback. A message already submitted may still complete once
  and remains visible. Failed requests are never automatically retried.
- Navigating away, hiding the tab, finishing or deleting stops
  voice mode. Transcripts longer than 2,000 characters are preserved for manual
  editing and are not automatically sent. The text composer remains available when voice mode is off. Supported browsers need
  HTTPS (or localhost), MediaRecorder, Web Audio and microphone permission.
- **Play AI voice** sends only a stored assistant reply from the active session
  for TTS. Audio is labelled AI-generated. Unsupported generation is replaced by
  the existing explicit unknown before it can be played. Paused scenes cannot play.

`POST /api/speech/transcribe` accepts multipart `file`, `language` and `consent`.
Media is limited to 4 MB and 120 seconds. FFmpeg selects the first audio track,
decodes to mono PCM at 16 kHz, blocks network protocols and has a 15-second timeout.
Temporary files are removed on success and failure. Whisper uses segment timestamps
and an explicit EN/DE/ES language; high no-speech-probability segments are dropped.
This does not eliminate transcription hallucination or assess pronunciation.

`POST /api/sessions` accepts reviewed `transcript` segments and
`transcript_confirmed=true`. Citations retain original segment times; chunking a
segment retains its interval, not a word-level timestamp. Edited text is explicitly
labelled a reviewed transcript. `POST /api/sessions/{id}/speech` accepts
`response_id` and `consent`, never arbitrary text, and returns MP3 without caching.
Whisper and TTS share the existing hourly provider-call ceiling; playback also
uses the session ceiling. Provider timeouts are 25 seconds with no retries.

Continuous voice uses the same speech endpoints and provider budget reservations.
Each completed voice exchange adds a transcription and a TTS call to the normal
chat calls; starting voice mode also synthesizes the current partner turn.
Generation and evidence review finish before playback begins, so pauses include
transcription, model validation and TTS latency. This is automatic turn-based voice,
not a low-latency speech-to-speech connection. No real-time provider API, new
provider credentials or backend protocol is required.

`npm run test:voice` exercises turn detection, validation-before-playback,
mute/interrupt, limits, safety, provider failure and stop/cancellation races using
browser API doubles. These checks make no provider calls and do not measure human
speech recognition accuracy or real provider latency.

For the optional browser integration check, install Playwright and its Chromium
browser, start the frontend, then run
`VOICE_TEST_URL=http://localhost:3000 node scripts/test_voice_browser.mjs`
(in PowerShell, set `$env:VOICE_TEST_URL='http://localhost:3000'` first).
`CHROME_PATH` optionally selects an installed Chrome executable;
`PLAYWRIGHT_MODULE` can point to an existing Playwright `index.mjs`.
The check uses a synthetic microphone file and real browser recording/playback
with mocked transcription/chat/TTS responses. It verifies the validation gate,
visible evidence, interruption, mute/stop, navigation/deletion, EN/DE/ES controls
and mobile layout. It makes no provider calls.

## Public video links

**Audio / video** combines recording, media uploads and video links in one source tab. Its video-link option accepts public HTTPS MP4/WebM/MOV URLs and YouTube video URLs. `POST /api/video/transcript` takes `url`, `language` and `consent`, returning
an editable preview without creating a session. Direct videos use the same
4 MB download cap and Whisper path as uploads. Direct links optionally accept `clip_start` (0–86,400 seconds) and `clip_seconds` (1–120 seconds), allowing a selected clip from a longer file. Without a clip selection, the original two-minute duration limit remains. YouTube imports the full available transcript in the selected language, rejecting text above 100,000 characters rather than silently truncating it, and labels generated captions. Caption lines are grouped into timestamped paragraphs and paginated for review, with a maximum of 1,000 blocks. Source timestamps can exceed 120 seconds; clip timestamps are offset to their position in the original video. Caption import is not audio recognition by this app.

Confirm the preview before creating a session. The source API accepts `video_url`
alongside reviewed segments and `transcript_confirmed=true`; stored source metadata
retains a canonical URL and timestamps. Signed direct-link query parameters are
stripped before persistence or model processing.

DNS validation pins the validated IP while TLS verifies the original hostname.
Every redirect is revalidated. Responses, request counts, time, concurrent imports
and hourly attempts are bounded. Private IPs, credentials, custom ports and
unsupported hosting pages are rejected. YouTube uses an unofficial caption SDK,
without proxies or login bypass. Missing captions/provider blocks offer paste/upload
fallbacks. Provider availability is not guaranteed by offline test results.

Eight new offline tests cover URL/DNS/redirect protections, pinned TLS, streamed
byte limits, media vs web-page handling, caption ingestion, consent and limits.

The expanded suite passes 77 tests. A browser check passed the video-link consent,
error fallback, transcript editing/confirmation and session creation flows using
stubbed caption responses. A real public CC0 MP4 was downloaded and decoded without
provider calls. Live YouTube caption availability has not been verified.

## Agent and evidence checks

The latest full-caption/combined-tab revision passes 80 backend tests and the
production build. A browser check with stubbed imports verified the single media
tab, upload/link switching, stale-source clearing, clip parameters, paginated
editing and actual source ingestion with evidence at 44 minutes. Real FFmpeg
tests verify selection of the requested interval. Hosted caption availability
and paid transcription remain separate validation work.

Live turns default to `backend/agent.py` preparation through LangChain
`ChatOpenAI.bind_tools`. The model chooses among `retrieve_evidence`,
`check_evidence`, `inspect_goal_progress` and `get_practice_hint`. Tools are read-only,
typed and bound to the current session. Tool inputs cannot supply a session ID.
Preparation uses at most two model calls and four tool calls, six-second provider
timeouts and an elapsed-time check. It can stop without tools. Returned tool names
appear in the turn API and synthetic evaluation reports.

The agent can retrieve additional passages before generation (up to eight unique
passages, combining the original top four and agent retrieval). Quote checks prove
literal presence only. Goal inspection reads validated state; it does not assess
new actions or write progress. The existing structured role-play and independent
semantic evidence review always follow preparation. The server alone commits goals
and turns. Invalid tools/arguments or budget failures leave the turn unsaved.
`REHEARSAL_AGENT_ENABLED=false` selects the previous fixed workflow explicitly.

## Persistent retrieval and deletion

Chroma `PersistentClient` is the local default. Each session owns a separate
collection named using a hash of its random bearer ID. Page, paragraph and timestamp
metadata survive persistence. The existing local 512-dimensional hashed embedding
baseline remains: storage is now a vector database, while semantic multilingual
embeddings remain future work. Memory mode is available as `VECTOR_STORE=memory`.

Activity updates a persisted wall-clock expiry. The cleanup task and startup purge
remove expired collections; explicit session deletion also removes a collection
when the conversation was lost in a restart. Collections can survive a process
restart until deletion/expiry; the in-memory conversation cannot be resumed.
Logical collection deletion does not promise secure disk erasure or deletion from
provider systems, filesystem backups or hosting snapshots. Operators must account
for backup retention when making deletion promises.

`render.yaml` keeps the existing free-host memory fallback. The optional
`render-persistent.yaml` configures a paid single-instance service and a 1 GB disk
mounted at `/home/rehearsal/data`, with Chroma beneath that path. Review charges
before applying it. No hosting plan has been changed. Disk-backed deployments have
an interruption during deploy and cannot scale horizontally. Verify write access,
restart retrieval and deletion on the actual mount before claiming hosted durability.

## LangSmith experiments and release gate

Set `LANGSMITH_API_KEY` only in the local evaluation environment or GitHub's
`evaluation` environment. Set `LANGSMITH_ENDPOINT` for your region when needed.
Normal HTTP requests force tracing off, regardless of tracing environment flags
or incoming headers. A process-local evaluation context enables traces only for
the explicitly invoked synthetic runner, including tools, retrieval, generation
and mandatory validation. Raw media is not traced.

```powershell
# Upload bundled fictional fixtures and trace deterministic demo evaluation:
python scripts/evaluate_langsmith.py
# Paid synthetic generation, tool selection and four model judges:
python scripts/evaluate_langsmith.py --live --judge
```

The runner versions the dataset name by content hash, creates a LangSmith
experiment and exports `.runtime/langsmith-evaluation.json`. It records source
hashes, model, retrieval settings, per-case elapsed time, tool selections,
deterministic checks, and optional correctness/relevance/groundedness/retrieval
relevance judges. LangChain model traces provide provider token usage when
returned. A failed metric fails the runner. No speech quality score is claimed:
recording fixtures and human-labelled transcription accuracy remain to measure.

The manual **LangSmith evaluation** GitHub workflow performs the same run and saves
its report. Add `LANGSMITH_API_KEY` and, for its paid option, `OPENAI_API_KEY` to the
`evaluation` environment. The manual **Release** workflow defaults to requiring a
successful evaluation workflow for the exact commit, in addition to CI. This gate
can accept a demo experiment; run the paid option to collect live-agent evidence.
Disabling the gate explicitly is supported for prototype deployment. Actual hosting
continues on Vercel/Render; this is not LangSmith application hosting.

## Verification and remaining evidence

```powershell
python -m unittest discover -s backend -t . -p 'test_*.py' -v
python scripts/evaluate_rag.py
npm run build
```

New offline tests exercise speech consent, silence/provider errors, temporary-file
cleanup, timestamp ingestion, playback isolation, model-selected tools, rejected
tool arguments, mandatory validation, trace boundaries and actual Chroma reads
from a second Python process. Existing live-workflow tests explicitly disable
preparation to test the original validator in isolation.

Local verification on 4 November 2026: 69 backend tests passed, all nine offline RAG
cases passed with Chroma, the Next.js production build passed, and both Render
Blueprints passed the current public JSON Schema. Real FFmpeg decoded synthetic
WAV and MP4 media. A Chrome check exercised source transcript correction/confirmation,
microphone recording into an unsent draft, Send, playback controls and deletion
without browser errors; its transcription/TTS responses were stubbed. See
[the verification record](../evaluation/multimodal-implementation-2026-11-04.json).

Complete a microphone/browser demonstration, real Whisper/TTS run, paid agent
benchmark and a LangSmith experiment in the target account before claiming those
integrations are validated against their hosted services. Docker and actual disk
mount behavior also require deployment-environment verification.

API references: [OpenAI transcription](https://developers.openai.com/api/reference/resources/audio/subresources/transcriptions/methods/create),
[OpenAI TTS](https://developers.openai.com/api/docs/guides/text-to-speech),
[LangChain tools](https://docs.langchain.com/oss/python/langchain/tools),
[LangSmith evaluation](https://docs.langchain.com/langsmith/evaluate-llm-application),
[Chroma persistence](https://docs.trychroma.com/reference/python/client),
[Render disks](https://render.com/docs/disks).
