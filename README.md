# The Rehearsal

**Measured quality:** [36-case baseline, failures and rent-conflict fix](evaluation/QUALITY_RESULTS.md).
On the same small synthetic fixture set, the local post-fix live run improved
answer-status accuracy from 83.3% to 91.7% and conflicting-price false confirmations
from 3/3 to 0/3. Goal precision remains 90.9%, recall 100%; keyword-only detection
still fails. These are reference-label metrics, not human-reviewed reliability estimates.

**Submission verification:** [current evidence and release status](SUBMISSION.md)
includes real multilingual speech, agent, browser and hosted LangSmith results.

**For capstone reviewers:** see [the evidence guide](CAPSTONE.md) for architecture,
prompt locations, reproducible checks, evaluation results, CI/CD status, guardrails
and cost/latency/scaling trade-offs. [Evaluation plan and runner](EVALUATION.md) and
[deployment setup](DEPLOYMENT.md) distinguish completed work from pending validation.

**Published app:** https://the-rehearsal-lab.vercel.app — the header identifies Live AI or Demo mode; visitors do not supply provider keys. The free backend may take time to wake after inactivity.

A session-only app for rehearsing real-life situations in **English, German or Spanish**. Bring a document, an Idealista advert link with optional pasted text, or describe your situation, choose an apartment viewing, job interview, course enquiry or difficult conversation, edit a mission checklist, rehearse in text or optional speech, get communication feedback, and retry a missed goal. It supports preparation in your own language as well as foreign-language practice.

The original visual design uses restrained rehearsal-room colors, mission cards and production notes. This is an independent real-life rehearsal project, with no affiliation or endorsement. The setup screen retains the existing Nathan Fielder reference picture, with its HBO/source credit and independent-project disclaimer, as requested.

Choose the **conversation language** and **feedback language** independently from English, German and Spanish. Missions and feedback use the feedback language; partner turns, sentence starters, phrase sheets and retry openings use the conversation language. An independent interface selector localizes controls, processing notices and errors into English, German or Spanish. The default frontend style is **Everyday conversation**: clear adult communication, with attention to tone, listening and next steps. B1 and B2 are optional styles for language learners. Demo scripts are shared across styles; live mode adapts linguistic complexity. Fictional samples are provided in all three languages. Uploaded documents stay in their original language; evidence is quoted verbatim, never silently translated.

## Run locally

Requirements: Python 3.11+ and Node.js 20.9+ (Node 22 recommended).

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
Copy-Item .env.example .env
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

In a second terminal:

```powershell
npm install
npm run dev
```

Open http://localhost:3000. A Next.js server route proxies `/api` to FastAPI at `127.0.0.1:8000`, or the server-only `BACKEND_URL` when set. The API has no public CORS allowance; run locally with a single backend worker. API reference: http://127.0.0.1:8000/docs. For a production frontend build, run `npm run build` then `npm start`. See [DEPLOYMENT.md](DEPLOYMENT.md) for Vercel frontend and single-instance backend hosting.

If this workspace contains the verification-only `.runtime/node.exe` and `.runtime/package/bin/npm-cli.js`, those can replace system Node/npm. They are ignored and are not required project files.

```powershell
# Alternative frontend launch with this workspace's downloaded runtime:
$env:Path = "$pwd/.runtime;" + $env:Path
.runtime/node.exe .runtime/package/bin/npm-cli.js run dev
```

## Demo and live modes

`.env.example` lists all variables:

| Variable | Default | Behavior |
| --- | --- | --- |
| `REHEARSAL_MODE` | `demo` | `demo` makes no model calls; `live` enables external generation. |
| `OPENAI_API_KEY` | empty | Required only in live mode; server-only. |
| `OPENAI_MODEL` | `gpt-4.1-mini` | Structured-output capable chat model. |

Restart FastAPI after changing variables. Demo works without a key in all three languages. Its conversation is scripted, but supported factual questions get extractive answers: a relevant retrieved sentence is quoted directly in the partner reply with a passage ID. Narrow multilingual rules cover rent, availability, pets, working hours, salary, class schedules and course prices. Missing, conflicting, instructional or unrecognised information is not confirmed. Informal questions without question marks receive an explicit unknown response rather than a generic acknowledgement. Rental employment/income-document requirements are outside the extractive demo: these stay unconfirmed and appear as a follow-up question in review. Quoted facts retain the document’s original language. These rules do not constitute general semantic QA. Goals use transparent, language-specific keyword rules for the learner’s **asked / practised** action; that is separate from whether a document answer was confirmed. Answer states are `not_asked`, `confirmed`, `unknown`, `not_applicable` and `unverified`. Unresolved questions remain in the debrief even after being asked. The prominent **Rehearse one moment again** section offers every goal for replay; unknown answers use a follow-up scene. Replay resets progress. Questions about utilities or deposits are routed separately from rent even when they contain the word “rent”; unknown utilities remain in the unanswered list. Feedback suggestions are matched to the quoted turn’s subject, not to a pending goal. If the demo has no specific correction, it says so without inventing a refinement. Valid citation IDs alone never confirm entailment. Live mode additionally requires exact source support and a separate evidence-review call before confirming an answer. Edited goals are supported but cannot be automatically assessed in demo. Demo translation supplies a labelled fixed phrase; arbitrary translation requires live mode. Feedback uses a few explicit Spanish correction rules where applicable and otherwise offers a labelled communication suggestion in the chosen feedback language. It is a demonstration, not an adaptive conversation model.

Live mode defaults to bounded LangChain tool-calling preparation before mandatory evidence validation. The model chooses retrieval, quote checks, goal inspection or practice guidance; tools cannot commit state. Live mode uses LangChain chat calls with strict JSON Schema outputs, validated again by Pydantic. A bounded role-play proposal is followed by a separate evidence-review function using the same configured model. The provider assesses fixed, required `goal_0` through `goal_n` slots rather than generating goal IDs or separate answer lists. The server binds those slots to its actual mission IDs (including replay IDs), then applies the same exact-quote and independent semantic/evidence checks. The schema also limits citation/source IDs to retrieved passages. This prevents goal-text/ID confusion and duplicate answer entries from aborting ordinary turns without relaxing source validation. Custom-goal progress requires an exact quote from the latest learner turn plus semantic acceptance. Previously validated historical goal observations are ignored rather than treated as new evidence. Answers need exact retrieved source quotes, valid IDs and review support to become confirmed. Unsupported generated answers are withheld and replaced by an explicit unknown response; no silent switch to demo occurs. Review is an additional check, not proof against every hallucination.

Translation hints return and validate the actual supplied phrase, its translation and an explanation. Debrief suggestions must quote real learner text and relate to that turn. The provider receives `store=false`; ordinary user-session tracing remains disabled; synthetic evaluation tracing is explicit, and the app makes no guarantee about the provider’s account-level retention policies.

The single backend instance limits provider calls to `MODEL_CALLS_PER_HOUR` (default 200), with at most 100 calls per session, 20-second provider timeouts, no SDK retries and capped output tokens. A role-play turn normally uses two calls. Counters contain timestamps/counts only and reset on restart; these are application request ceilings, not an account billing limit. Failed calls consume a reservation. Set provider-level spend limits separately.

The UI waits for server mode before enabling setup. Live missions require `external_model_consent=true`, sent by the updated client after displaying the processing notice. Older open demo tabs are told to refresh before a live mission; their old notice cannot silently authorize model processing.

## Remember your language practice

At the review, explicitly save a named take to **My saved rehearsals**. Revisit
conversations, feedback and phrase sheets, filter by language/scenario and compare
two attempts. Saved copies stay in this browser after server-session deletion;
remove one or clear the library whenever you want. Original files, source cards
and audio are excluded. There is no account, cross-device sync or live-session
resumption. Download important takes as a backup. See [storage and privacy](docs/REHEARSAL_LIBRARY.md).

## Voice rehearsal

**Learning from real use:** visitors can optionally share an anonymous rating and
category after a rehearsal. Shared ratings are stored separately without source
or conversation text. Generate your private evaluation report with
`python scripts/report_feedback.py --html .runtime/feedback-report.html`.
See [consent, metrics, retention and durable-hosting requirements](docs/USER_FEEDBACK.md).

With `SPEECH_ENABLED=true`, the conversation offers **Rehearse out loud**.
Accept its audio-processing notice and select **Start voice rehearsal**. Speak
and pause: your transcript is automatically sent as a message, the normal source
checks run, and the partner's validated reply plays automatically. Transcripts,
citations and mission progress remain visible. A short 1.2-second pause ends your
turn; mute, interrupt playback or stop at any time. Typing remains available when voice mode is off; source media uploads stay under Audio / video.

This is turn-based voice with pauses for transcription, validation and playback,
not simultaneous speech-to-speech streaming. Microphone audio and synthesized
replies use OpenAI even in demo mode. See [behavior, limits and verification](docs/MULTIMODAL.md#speech-workflow).

## Situation sources, video links and dialogue maps

The source screen has three tabs: **Try a sample**, **Your situation** and
**Audio / video**. Under **Your situation**, choose text, a document upload or
an optional listing link. Each choice keeps its own draft; only the selected
source type is used when building a mission.

The **Audio / video** tab combines recording, uploads and video links. Its video-link option accepts public HTTPS MP4/WebM/MOV file links and YouTube
video links. Direct files must be at most 4 MB; transcribe a video up to two minutes or choose a start time and a clip of 1–120 seconds from a longer file. Audio is sent to Whisper after consent. YouTube imports the full available captions in the selected conversation language, up to 100,000 characters, without downloading the video.
Review/edit the timestamped transcript and confirm it before building a mission.
Source citations retain the video URL and timestamps. Signed URL query parameters
are not retained.

Other hosting pages (including Vimeo/Loom pages), private/login-protected media,
missing captions and blocked requests fall back to pasted text or media upload.
YouTube uses the unofficial `youtube-transcript-api` package; provider changes and
hosting-IP blocks can prevent imports. It does not bypass restrictions. Fetches
reject private-network destinations, pin validated IPs for TLS, recheck redirects,
and bound bytes, time and concurrency.

Choose **Your situation**, then **Use a listing link (optional)** for a direct HTTPS Idealista advert from Spain, Portugal or Italy. If public reading is permitted, the server extracts visible text and stores the URL with paragraph evidence for this session. Redirects are restricted, private network destinations are rejected, payloads/timeouts are bounded, robot exclusions are checked, and blocked/login/challenge pages are not bypassed. The listing can change; the original link remains available in evidence cards.

Many Idealista reads are blocked. The reliable fallback is to paste the advert’s price, description and features into the optional text field. The UI labels this **user-pasted text, not fetched from the site**. This is not an official Idealista API integration. [Official Search API access requires a separate application](https://developers.idealista.com/access-request); no API access or third-party scraping service is bundled.

During mission review, **A plan for the unplanned** maps each goal to three possible conversational paths. Branch buttons explore clear answers, missing details and questions asked back. The map starts collapsed under **Explore possible responses** on the plan step. The rehearsal sidebar keeps only the mission and hints. These plans are hypothetical communication sketches, never predictions or new document facts. No map selections are saved beyond the current page session.

## Try a complete rehearsal

1. Select the fictional **Casa Oliva** property listing. Choose **Apartment viewing**, Spanish, B1 and English feedback for this example. The frontend defaults to English / Everyday; German is also supported.
2. Select **Build my mission**, review/edit the three observable goals, then begin.
3. Send `Cuanto cuesta el alquiler?` The partner quotes the document’s €850 monthly rent sentence with a citation. The mission separately shows **Asked / practised: Yes** and **Answer: Confirmed by source**.
4. Use **Help me** for a starter or vocabulary. Ask `¿Cuándo está disponible el piso?`.
5. Finish and reflect. Goal achievement, English language feedback quoting your text, unanswered questions and a Spanish phrase sheet appear separately. The missing opening question mark gets feedback.
6. Select **Rehearse this moment** for the missed pets question. Send `¿Se admiten mascotas?`. The evidence says this is unspecified; the app makes no promise that pets are allowed. Finish the targeted scene.
7. Select **End session & delete data**. The frontend requests deletion, checks that the session status endpoint returns 404, and only then clears document and conversation state and displays the server-deletion confirmation. This verifies session inaccessibility, not cryptographic memory erasure.

For a communication-focused example, choose the fictional **Saying no to family** sample under **A difficult conversation**. A family member asks for help with errands this weekend; you have decided you cannot help. Practise declining, asking them not to assume your availability, and holding that boundary if they ask again. No apology, detailed explanation, alternative offer or successful agreement is required. The notes do not assign a particular relative or invent a family history. The sample, goals, hints and phrase sheet are available in English, German and Spanish. The demo partner gives modest scripted pushback; custom situations retain their own context instead of inheriting this sample.

Other fictional sample documents live in `samples/`. Pasted text, text PDFs and DOCX also work. Uploads are limited to 4 MB, PDFs to 100 pages, expanded DOCX contents to 20 MB, and extracted text to 100,000 characters. Encrypted PDFs and scans without text are rejected. DOCX paragraph and PDF page metadata are preserved. Custom document loading implements LangChain’s `BaseLoader` in memory; no permanent file path is created.

## Architecture

The [multimodal implementation guide](docs/MULTIMODAL.md) covers speech activation,
LangSmith experiments, the tool-calling agent and persistent Chroma. Real speech, agent and hosted LangSmith checks passed; deployment results are
recorded on the [v0.7.0 release](https://github.com/zinaelnahel/the-rehearsal/releases/tag/v0.7.0). The public free host uses memory retrieval; persistent Chroma is demonstrated locally.
The [architecture image prompt](docs/architecture-image-prompt.txt) reflects the
implementation and labels deployment-dependent capabilities.

- **Frontend:** Next.js App Router + React, responsive original CSS, keyboard-accessible native inputs, explicit labels, visible focus states, live conversation/error regions, reduced-motion styling and collapsible source cards.
- **Backend:** FastAPI, Pydantic schemas, a single explicit session state machine: `setup → mission → chat → debrief → chat (targeted retry)`; deletion is allowed from every phase. Actions in the wrong phase return 409.
- **RAG:** LangChain loaders, `RecursiveCharacterTextSplitter`, local deterministic 512-dimensional hashed word embeddings through LangChain’s `Embeddings`, and persistent Chroma by default (`VECTOR_STORE=memory` selects `InMemoryVectorStore`). Retrieval is lexical with a small English/German/Spanish alias map, keeping demo and live embeddings local. The initial search retrieves four chunks; agent retrieval can expand live context to eight unique chunks. It is not a pretrained semantic embedding model; cross-language retrieval is limited.
- **State:** random bearer session IDs, per-session retrieval collection, role/scenario, language/level, mission, turns, hints and goal evidence; Chroma stores source text/vectors and expiry metadata on disk. No accounts or persistent server conversation checkpoints. Optional, explicitly saved browser archives use IndexedDB and cannot resume expired sessions. Calls to a session are serialized for chat and finish.

## Privacy and trust boundaries

Documents are processed **on the server**, not just on the device. Upload multipart parsing may temporarily spool larger files to the OS temporary directory; the upload is closed and its temporary backing file removed immediately after parsing. With Chroma, extracted source text and vectors are stored in the configured database directory until deletion/expiry. Memory mode keeps them in process memory. Live conversation state stays in server memory; neither retrieval mode saves conversations to server disk or logs. Separately, you can explicitly save a source-free conversation/review snapshot in this browser for language practice; it remains after server-session deletion until removed from the library or browser data. The optional review download creates a file on your device only when you request it. API responses use `Cache-Control: no-store`; Ordinary user-session tracing is disabled; the explicit synthetic LangSmith runner uploads fictional fixtures and traces. Do not enable request-body logging or proxy caching.

**End & delete session** deletes server references and its persisted retrieval collection, verifies a subsequent `/api/sessions/{id}/status` request returns 404, and clears visible client data only after that verification. Closing the tab attempts best-effort deletion with a keepalive request. Browser crashes/offline closes cannot guarantee that request; abandoned sessions expire after one hour of inactivity and a cleanup task runs every 30 seconds. Expiry also occurs before every action. Restarting the single backend process clears conversation sessions. Chroma collections survive until explicit deletion or persisted idle expiry; startup and periodic cleanup purge expired collections. Process memory deletion is reference deletion, not cryptographic zeroization. Collection deletion is logical deletion, not secure disk erasure or removal from hosting snapshots/backups. Local browser/OS memory and external provider retention are outside this app’s control.

In live mode, retrieved passages and conversation data are sent to OpenAI; provider handling is subject to your account’s policies. This notice appears before starting. Keys never reach the browser. Demo chat makes no external model calls. Optional speech sends recordings or stored partner replies to OpenAI after the displayed processing notice. Google Fonts is used for typography; it is a third-party font request and receives no document or conversation text.

Uploaded text is untrusted data, never executable instructions. It is passed separately under `retrieved_passages` and described as untrusted in live system prompts. React escapes displayed text. The preparation agent can choose only typed, read-only, session-bound retrieval, quote-check, goal-inspection and practice-guidance tools. It has no shell or arbitrary browsing. Mandatory server evidence checks cannot be skipped. A separate user-requested URL importer is restricted to validated Idealista listing URLs. Prompt injection and hallucination are reduced, not eliminated; citation-ID checking alone does not prove entailment. Use the evaluation plan before any public rollout.

## Verification

```powershell
python -m unittest backend.test_app backend.test_live backend.test_listings backend.test_context_feedback -v
npm run build
```

Tests exercise all 36 scenario/conversation-language/feedback-language combinations, the full demo flow, evidence locations, mission editing, hints, debrief, retry, deletion, session isolation, expiry, phase guards, upload validation, DOCX parsing and untrusted document text. See [EVALUATION.md](EVALUATION.md) for quality evaluation and live-model release gates.

## Known limitations

English, German and Spanish only; interface language is selected independently from conversation and feedback language. Text chat plus optional Whisper transcription and AI voice playback (enable speech on the backend). The demo is intentionally scripted and its keyword rules can misclassify achievement. No OCR, legacy DOC files, authentication, synchronized history, distributed sessions or semantic embeddings. The optional on-device rehearsal library is separate from live sessions. Synthetic real-provider speech and browser checks passed; broad human speech accuracy remains unmeasured. Replay focuses only on the selected goal and replaces the previous scene’s turns/debrief. Model feedback and goal detection need human review. File reads, interrupted uploads or response-body reads, deletion verification failures, non-JSON gateway errors and cold-start timeouts produce actionable messages; transient network failures can still occur, and mutations are not automatically retried. Live evidence checks combine exact quotations and a model review; human evaluation is still needed. This unauthenticated prototype is not production-validated: verify transport security, edge controls, the required parser sandbox on your host, durable budget storage and provider billing limits before rollout. Current limits include 100 active sessions, 30 learner turns per scene, 30 hints per session and one-hour idle expiry.

## Navigation and optional download

**Action - start Take 01** begins the planned scene; **Cut - finish & reflect** ends it and opens review. These use the existing start/finish actions with no countdown, audio or extra step. Completed progress steps are clickable, with explicit Back controls. Revisiting the source or editing a draft plan does not change the active conversation or its scenario/language. Returning to the conversation preserves an unsent reply. Applying a new source or restarting an edited plan asks before replacing the current take; a failed new mission leaves the existing session available. Replay also warns before replacement.

From review, **Back to the conversation** opens the finished dialogue for rereading. **Continue conversation** resumes the same messages and goals, discards the old review/rating, and generates a fresh review when you finish again. Browsing between review and other steps preserves the current rating.

The review offers **Download conversation (.txt)**. This explicit action creates a UTF-8 text file in the browser containing only the current take's dialogue and review (goals, communication notes, open questions and phrases). It makes no export API call, sends nothing extra to a provider, and does not use localStorage or add server persistence. The downloaded file remains on the user's device after session deletion. There is no automatic download or archive of earlier takes. If the server reports an expired/deleted session, the app explains timeout/restart possibilities and offers a download of any locally visible dialogue before starting again; source selections and typed context remain in the form. This recovery cannot restore a server session or data lost when a tab closes.

## Response feedback and sensitive scenes

The review offers one optional thumbs-up/down rating for the whole dialogue, after finishing. There are no per-turn rating controls in the conversation. Select the same rating again or Clear to remove it; changing ratings replaces the previous value. Thumbs-down offers an optional predefined reason. `PUT /api/sessions/{sid}/responses/{response_id}/feedback` accepts only rating and reason; the server supplies scenario and an opaque dialogue/version identifier. The existing response-feedback API also accepts the review identifier, recorded with version `dialogue-0.6`. Unknown fields (including conversation text) are rejected. Feedback is held in session memory, cleared on replay, deletion, expiry or restart, and is never sent to the model or used as automatic training labels. No free-text explanations or conversation-reporting feature is included, so there is no transcript-sharing consent step. There is no durable aggregate review/dashboard in this architecture.

Partner dialogue stays in character; coaching belongs in the review. Live generation receives the stated outcome in missions, hints, dialogue and review. Demo includes a specific final-breakup pack in all three supported languages; other demo situations remain scripted and require mission editing for custom needs. Emotional dialogue-map paths preserve boundaries without assuming compromise or continued contact.

The app does not scan context, goals or messages for danger keywords or automatically pause sensitive conversations. Users can continue, review, replay or end their rehearsal. The app is conversation practice, not therapy or emergency support.

## Live validation record

The real-provider smoke evaluation on 2 November 2026 used only fictional adverts in English, German and Spanish: 27 calls in the final passing run. It checked negated custom goals, actual goal questions, context-dependent follow-ups, real supplied-phrase translations, exact debrief quotes, replay and deletion. See [the synthetic report](evaluation/live-smoke-2026-11-02.json) and [EVALUATION.md](EVALUATION.md). These are small smoke checks, not broad accuracy, retrieval-recall or clinical-effectiveness measurements. A LangSmith synthetic experiment runner is now implemented; two hosted experiments have passed; a teacher-reviewed benchmark remains future work.


To explicitly repeat the real-provider fictional smoke run from the repository root: `python scripts/evaluate_live.py`. This uses the server key, makes provider calls and writes a local report to ignored `.runtime/live-evaluation.json`; it is not run by the deterministic unit/integration test command.

## Rent-turn validation regression

The previous live smoke check edited mission goals, which missed a failure in default generated apartment missions. A fresh synthetic reproduction returned goal text as a goal ID and failed validation. The fixed-slot contract removes model-authored goal IDs from generation; invalid quotes and unsupported answers are still rejected/withheld.

To repeat the stronger real-provider regression with fictional samples only:

```powershell
python scripts/evaluate_rent_flow.py
```

This deliberately makes provider calls (40 in the recorded passing run), creates eight fresh default apartment takes, checks ordinary/informal rent phrasings, source-confirmed progress, follow-ups, actual-turn review quotes, replay and deletion, and writes a synthetic report to ignored `.runtime/rent-flow-evaluation.json`. English rent variants repeat twice; German and Spanish are included. See [the report](evaluation/rent-fixed-slots-2026-11-02.json). The existing multilingual smoke regression also passed with the new contract (27 calls). These finite smoke checks are not broad reliability metrics.

## Prompt context savings

Model-facing history preserves the original role and dialogue text but excludes stored source payloads and response metadata. This avoids repeatedly sending historical passages alongside current retrieval. It applies to agent preparation, generation, independent evidence review, hints and debriefs. Current retrieved passages remain complete; citation checks, review calls and model selection are unchanged. Saved turns still retain source evidence for the UI and downloads.

Run `python scripts/evaluate_prompt_context.py` for an offline size comparison. Ten synthetic exchanges using the fictional EN/DE/ES samples reduced serialized **history bytes** by 71–74%. This excludes system prompts, schemas and current retrieval; it is neither an overall token reduction nor a measured billing saving. The optimization adds no provider calls. Real provider token usage and quality comparisons remain to be measured.

## Hosted YouTube caption fallback

When direct YouTube reads fail, the configured backend can fetch existing captions through Supadata in native-only mode. Both user-provided video links passed [hosted verification](evaluation/supadata-hosted-check-2026-11-04.json). Captions still require review; availability and service quotas apply. See [setup, privacy and verification details](docs/SUPADATA.md).


## Hardening update (5 November 2026)

The interface now has an independent EN/DE/ES selector covering controls,
consent/privacy notices, navigation and errors. Original source quotations and
user-authored text are not translated. Language values sent to the backend remain
canonical regardless of the interface language.

API mutations have configurable single-instance ceilings of 300 requests/minute,
12 concurrent requests, and 30 requests/minute per proxy-identified client.
Vercel's overwritten client-IP header is hashed with the proxy secret and UTC day;
raw IPs are not forwarded or retained by this application. Deletes and reads stay
available during throttling. Provider calls reserve a configurable amount from an
atomic SQLite daily allowance before dispatch, including failed calls and optional
caption-service requests. Input bytes and output tokens are bounded. These are
conservative application reservations, not a provider billing guarantee; configure
provider spend controls too. The ledger survives process restarts, but needs durable
storage to survive host replacement.

PDF/DOCX parsing runs in disposable subprocesses with a 12-second deadline, two
parser slots, filtered secrets and Linux resource limits. Docker requires Landlock
ABI 3 plus seccomp: runtime libraries are read-only, application data is inaccessible,
networking and subprocess creation are denied. Unsupported hosts reject document
imports with a text-paste fallback. CI now runs a sandbox confinement probe inside
the image. Native Linux confinement has not been executed on this Windows machine.

Video language changes preserve URL, pasted text and fetch consent while explaining
why transcript confirmation must be renewed. Wrong-language caption responses are
rejected before source creation. Listing instructions explain paste-and-retry.

Verification includes the production build, complete EN/DE/ES browser journeys,
real PDF/DOCX uploads, a synthetic-microphone MediaRecorder journey, real FFmpeg
format decoding, hostile-document tests, and a 126-case offline quality report.
The report exposes scripted-demo limitations; it is not a human quality score.

See [release status and commands](docs/RELEASE_GATES.md). The production release
workflow now requires current, hash-bound human-reviewed live benchmark evidence.
No human verdicts, physical-device results or public deployments were fabricated.


## Partner role ownership regression

A reported family-boundary exchange had the family member reply with the
learner's refusal. Roles were present in the generation prompt, but the broad
review verdict could still approve words assigned to the wrong speaker.
Evidence review now requires an explicit `partner_role_consistent` verdict;
source confirmation also depends on it. The known family-request scenario adds
an independent EN/DE/ES check for first-person refusals and ownership reversals
of the learner's boundary. A rejected reply is replaced by an in-role clarification
without invented source evidence, while independently validated learner actions
remain separate. Generic factual withholding retains its existing behavior.

Regression checks include the reported wording, multilingual variants, correct
second-person reflections, and a normal rent question. The final real-provider
run used 30 calls with fictional EN/DE/ES family scenes and a rent regression;
all passed. A bad proposal was caught even when the model reviewer approved it.
See [the synthetic report](evaluation/family-roles-live-2026-11-05.json). This is
finite model testing, not human-reviewed reliability. Repeat explicitly with
`python scripts/evaluate_family_roles.py` (paid provider calls).
