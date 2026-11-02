# The Rehearsal

**Published app:** https://the-rehearsal-lab.vercel.app — the header identifies Live AI or Demo mode; visitors do not supply provider keys. The free backend may take time to wake after inactivity.

A session-only app for rehearsing real-life situations in **English, German or Spanish**. Bring a document, an Idealista advert link with optional pasted text, or describe your situation, choose an apartment viewing, job interview, course enquiry or difficult conversation, edit a mission checklist, rehearse in text, get communication feedback, and retry a missed goal. It supports preparation in your own language as well as foreign-language practice.

The original visual design takes inspiration from the controlled sets and documentary production notes of Nathan Fielder’s *The Rehearsal*. This is an independent real-life rehearsal project, with no affiliation or endorsement. The setup screen credits the inspiration and uses a series still as an illustrative reference, with a source link; it is not an original app-generated image.

Choose the **conversation language** and **feedback language** independently from English, German and Spanish. Missions and feedback use the feedback language; partner turns, sentence starters, phrase sheets and retry openings use the conversation language. Interface labels remain in English. The default frontend style is **Everyday conversation**: clear adult communication, with attention to tone, listening and next steps. B1 and B2 are optional styles for language learners. Demo scripts are shared across styles; live mode adapts linguistic complexity. Fictional samples are provided in all three languages. Uploaded documents stay in their original language; evidence is quoted verbatim, never silently translated.

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

Restart FastAPI after changing variables. Demo works without a key in all three languages. Its conversation is scripted, but supported factual questions get extractive answers: a relevant retrieved sentence is quoted directly in the partner reply with a passage ID. Narrow multilingual rules cover rent, availability, pets, working hours, salary, class schedules and course prices. Missing, conflicting, instructional or unrecognised information is not confirmed. Quoted facts retain the document’s original language. These rules do not constitute general semantic QA. Goals use transparent, language-specific keyword rules for the learner’s **asked / practised** action; that is separate from whether a document answer was confirmed. Answer states are `not_asked`, `confirmed`, `unknown`, `not_applicable` and `unverified`. Unresolved questions remain in the debrief even after being asked. The prominent **Rehearse one moment again** section offers every goal for replay; unknown answers use a follow-up scene. Replay resets progress. Questions about utilities or deposits are routed separately from rent even when they contain the word “rent”; unknown utilities remain in the unanswered list. Feedback suggestions are matched to the quoted turn’s subject, not to a pending goal. If the demo has no specific correction, it says so without inventing a refinement. Valid citation IDs alone never confirm entailment. Live mode additionally requires exact source support and a separate evidence-review call before confirming an answer. Edited goals are supported but cannot be automatically assessed in demo. Demo translation supplies a labelled fixed phrase; arbitrary translation requires live mode. Feedback uses a few explicit Spanish correction rules where applicable and otherwise offers a labelled communication suggestion in the chosen feedback language. It is a demonstration, not an adaptive conversation model.

Live mode uses LangChain chat calls with strict JSON Schema outputs, validated again by Pydantic. A bounded role-play proposal is followed by a separate evidence-review function using the same configured model. Custom-goal progress requires an exact quote from the latest learner turn plus semantic acceptance. Previously validated historical goal observations are ignored rather than treated as new evidence. Answers need exact retrieved source quotes, valid IDs and review support to become confirmed. Unsupported generated answers are withheld and replaced by an explicit unknown response; no silent switch to demo occurs. Review is an additional check, not proof against every hallucination.

Translation hints return and validate the actual supplied phrase, its translation and an explanation. Debrief suggestions must quote real learner text and relate to that turn. The provider receives `store=false`; tracing remains disabled, and the app makes no guarantee about the provider’s account-level retention policies.

The single backend instance limits provider calls to `MODEL_CALLS_PER_HOUR` (default 200), with at most 100 calls per session, 20-second provider timeouts, no SDK retries and capped output tokens. A role-play turn normally uses two calls. Counters contain timestamps/counts only and reset on restart; these are application request ceilings, not an account billing limit. Failed calls consume a reservation. Set provider-level spend limits separately.

The UI waits for server mode before enabling setup. Live missions require `external_model_consent=true`, sent by the updated client after displaying the processing notice. Older open demo tabs are told to refresh before a live mission; their old notice cannot silently authorize model processing.

## Listing links and dialogue maps

Choose **Listing link** for a direct HTTPS Idealista advert from Spain, Portugal or Italy. If public reading is permitted, the server extracts visible text and stores the URL with paragraph evidence for this session. Redirects are restricted, private network destinations are rejected, payloads/timeouts are bounded, robot exclusions are checked, and blocked/login/challenge pages are not bypassed. The listing can change; the original link remains available in evidence cards.

Many Idealista reads are blocked. The reliable fallback is to paste the advert’s price, description and features into the optional text field. The UI labels this **user-pasted text, not fetched from the site**. This is not an official Idealista API integration. [Official Search API access requires a separate application](https://developers.idealista.com/access-request); no API access or third-party scraping service is bundled.

During mission review, **A plan for the unplanned** maps each goal to three possible conversational paths. Branch buttons explore clear answers, missing details and questions asked back. The chat sidebar contains the same map in an expandable panel. These plans are hypothetical communication sketches, never predictions or new document facts. No map selections are saved beyond the current page session.

## Try a complete rehearsal

1. Select the fictional **Casa Oliva** property listing. Choose **Apartment viewing**, Spanish, B1 and English feedback for this example. The frontend defaults to English / Everyday; German is also supported.
2. Select **Build my mission**, review/edit the three observable goals, then begin.
3. Send `Cuanto cuesta el alquiler?` The partner quotes the document’s €850 monthly rent sentence with a citation. The mission separately shows **Asked / practised: Yes** and **Answer: Confirmed by source**.
4. Use **Help me** for a starter or vocabulary. Ask `¿Cuándo está disponible el piso?`.
5. Finish and reflect. Goal achievement, English language feedback quoting your text, unanswered questions and a Spanish phrase sheet appear separately. The missing opening question mark gets feedback.
6. Select **Rehearse this moment** for the missed pets question. Send `¿Se admiten mascotas?`. The evidence says this is unspecified; the app makes no promise that pets are allowed. Finish the targeted scene.
7. Select **End session & delete data**. The frontend requests deletion, checks that the session status endpoint returns 404, and only then clears document and conversation state and displays the server-deletion confirmation. This verifies session inaccessibility, not cryptographic memory erasure.

For a communication-focused example, select **A difficult conversation** with German / Everyday and English feedback. Send `Ich fühle mich verunsichert, wenn sich Pläne kurzfristig ändern.` Then ask `Wie siehst du die Situation?` and propose `Können wir einen nächsten Schritt vereinbaren?` The mission covers explaining a concern without blame, asking for another perspective and proposing a next step. The fictional demo never claims the other person agreed.

Other fictional sample documents live in `samples/`. Pasted text, text PDFs and DOCX also work. Uploads are limited to 4 MB, PDFs to 100 pages, expanded DOCX contents to 20 MB, and extracted text to 100,000 characters. Encrypted PDFs and scans without text are rejected. DOCX paragraph and PDF page metadata are preserved. Custom document loading implements LangChain’s `BaseLoader` in memory; no permanent file path is created.

## Architecture

- **Frontend:** Next.js App Router + React, responsive original CSS, keyboard-accessible native inputs, explicit labels, visible focus states, live conversation/error regions, reduced-motion styling and collapsible source cards.
- **Backend:** FastAPI, Pydantic schemas, a single explicit session state machine: `setup → mission → chat → debrief → chat (targeted retry)`; deletion is allowed from every phase. Actions in the wrong phase return 409.
- **RAG:** LangChain loaders, `RecursiveCharacterTextSplitter`, local deterministic 512-dimensional hashed word embeddings through LangChain’s `Embeddings`, and `InMemoryVectorStore`. Retrieval is lexical with a small English/German/Spanish alias map, keeping demo and live embeddings local. Top four chunks are retrieved per role-play turn. It is not a pretrained semantic embedding model; cross-language retrieval is limited.
- **State:** random bearer session IDs, per-session vector store, role/scenario, language/level, mission, turns, hints and goal evidence; no database, accounts, localStorage, persistent checkpointing or long-term memory. Calls to a session are serialized for chat and finish.

## Privacy and trust boundaries

Documents are processed **on the server**, not just on the device. Upload multipart parsing may temporarily spool larger files to the OS temporary directory; the upload is closed and its temporary backing file removed immediately after parsing. Extracted text, vectors and conversation state remain in process memory. Nothing intentionally saves them to disk, logs or browser storage. API responses use `Cache-Control: no-store`; LangChain tracing is disabled. Do not enable request-body logging or proxy caching.

**End & delete session** deletes server references, verifies a subsequent `/api/sessions/{id}/status` request returns 404, and clears visible client data only after that verification. Closing the tab attempts best-effort deletion with a keepalive request. Browser crashes/offline closes cannot guarantee that request; abandoned sessions expire after one hour of inactivity and a cleanup task runs every 30 seconds. Expiry also occurs before every action. Restarting the single backend process clears all sessions. Process memory deletion is reference deletion, not cryptographic zeroization. Local browser/OS memory and external provider retention are outside this app’s control.

In live mode, retrieved passages and conversation data are sent to OpenAI; provider handling is subject to your account’s policies. This notice appears before starting. Keys never reach the browser. Demo makes no external model calls. Google Fonts is used for typography; it is a third-party font request and receives no document or conversation text.

Uploaded text is untrusted data, never executable instructions. It is passed separately under `retrieved_passages` and described as untrusted in live system prompts. React escapes displayed text. Only the fixed retrieval/hint/mission functions are exposed by the application. The role-play model has no shell, arbitrary browsing, or tool execution. A separate user-requested URL importer is restricted to validated Idealista listing URLs. Prompt injection and hallucination are reduced, not eliminated; citation-ID checking alone does not prove entailment. Use the evaluation plan before any public rollout.

## Verification

```powershell
python -m unittest backend.test_app backend.test_live backend.test_listings -v
npm run build
```

Tests exercise all 36 scenario/conversation-language/feedback-language combinations, the full demo flow, evidence locations, mission editing, hints, debrief, retry, deletion, session isolation, expiry, phase guards, upload validation, DOCX parsing and untrusted document text. See [EVALUATION.md](EVALUATION.md) for quality evaluation and live-model release gates.

## Known limitations

English, German and Spanish only; interface labels remain English. Text chat only. The demo is intentionally scripted and its keyword rules can misclassify achievement. No OCR, legacy DOC files, speech, authentication, history, distributed sessions, semantic embeddings or analytics. Replay focuses only on the selected goal and replaces the previous scene’s turns/debrief. Model feedback and goal detection need human review. File reads, interrupted uploads or response-body reads, deletion verification failures, non-JSON gateway errors and cold-start timeouts produce actionable messages; transient network failures can still occur, and mutations are not automatically retried. Live evidence checks combine exact quotations and a model review; human evaluation is still needed. Do not expose this unauthenticated prototype directly to the public internet: add transport security, deployment origin configuration, appropriate parser isolation, abuse controls and model cost limits first. Current limits include 100 active sessions, 30 learner turns per scene, 30 hints per session and one-hour idle expiry.

## Inspiration image

The setup image matches the Nathan Fielder laptop-harness reference supplied by the user. It is served locally from `public/images/rehearsal-inspiration.jpg` (about 49 KB), with visible HBO/source credit. Source: [Slashfilm’s image/article](https://www.slashfilm.com/1894836/nathan-for-you-real/). Its humorous app caption is original project copy, not a quote attributed to Nathan Fielder. The app is independent and unaffiliated.

## Live validation record

The real-provider smoke evaluation on 2 November 2026 used only fictional adverts in English, German and Spanish: 27 calls in the final passing run. It checked negated custom goals, actual goal questions, context-dependent follow-ups, real supplied-phrase translations, exact debrief quotes, replay and deletion. See [the synthetic report](evaluation/live-smoke-2026-11-02.json) and [EVALUATION.md](EVALUATION.md). These are small smoke checks, not broad accuracy, retrieval-recall or clinical-effectiveness measurements. LangSmith and a teacher-reviewed benchmark remain future evaluation work.
