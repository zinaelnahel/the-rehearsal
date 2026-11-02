# The Rehearsal

A session-only app for rehearsing real-life situations in **English, German or Spanish**. Bring a document or describe your situation, choose an apartment viewing, job interview, course enquiry or difficult conversation, edit a mission checklist, rehearse in text, get communication feedback, and retry a missed goal. It supports preparation in your own language as well as foreign-language practice.

The original visual design takes inspiration from the controlled sets and documentary production notes of Nathan Fielder’s *The Rehearsal*. This is an independent real-life rehearsal project, with no affiliation or official assets.

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

Restart FastAPI after changing variables. Demo works without a key in all three languages. Its replies are deliberately scripted; exact retrieved passages are shown in expandable evidence cards rather than paraphrased into potentially unsupported answers. Goals use transparent, language-specific keyword rules. Edited goals are supported but cannot be automatically assessed in demo. Demo translation supplies a labelled fixed phrase; arbitrary translation requires live mode. Feedback uses a few explicit Spanish correction rules where applicable and otherwise offers a labelled communication suggestion in the chosen feedback language. It is a demonstration, not an adaptive conversation model.

Live mode uses LangChain model calls and Pydantic structured outputs for missions, role-play, hints, and debrief. Retrieved text, recent conversation turns, missions, and feedback are separate fields. A bounded partner receives only the selected session’s passages, mission status and short history. The server orchestrates retrieval and hints; the model cannot run arbitrary tools or create other agents. Invalid citation IDs are rejected, and feedback quotes must exactly match a learner turn. Provider errors are shown without committing the failed learner turn.

## Try a complete rehearsal

1. Select the fictional **Casa Oliva** property listing. Choose **Apartment viewing**, Spanish, B1 and English feedback for this example. The frontend defaults to English / Everyday; German is also supported.
2. Select **Build my mission**, review/edit the three observable goals, then begin.
3. Send `Cuanto cuesta el alquiler?` The rent goal is detected in demo, and evidence includes the fictional €850 monthly rent with a section reference.
4. Use **Help me** for a starter or vocabulary. Ask `¿Cuándo está disponible el piso?`.
5. Finish and reflect. Goal achievement, English language feedback quoting your text, unanswered questions and a Spanish phrase sheet appear separately. The missing opening question mark gets feedback.
6. Select **Rehearse this moment** for the missed pets question. Send `¿Se admiten mascotas?`. The evidence says this is unspecified; the app makes no promise that pets are allowed. Finish the targeted scene.
7. Select **End session & delete data**. Its server session and vector store become unreachable; the frontend clears document and conversation state.

For a communication-focused example, select **A difficult conversation** with German / Everyday and English feedback. Send `Ich fühle mich verunsichert, wenn sich Pläne kurzfristig ändern.` Then ask `Wie siehst du die Situation?` and propose `Können wir einen nächsten Schritt vereinbaren?` The mission covers explaining a concern without blame, asking for another perspective and proposing a next step. The fictional demo never claims the other person agreed.

Other fictional sample documents live in `samples/`. Pasted text, text PDFs and DOCX also work. Uploads are limited to 4 MB, PDFs to 100 pages, expanded DOCX contents to 20 MB, and extracted text to 100,000 characters. Encrypted PDFs and scans without text are rejected. DOCX paragraph and PDF page metadata are preserved. Custom document loading implements LangChain’s `BaseLoader` in memory; no permanent file path is created.

## Architecture

- **Frontend:** Next.js App Router + React, responsive original CSS, keyboard-accessible native inputs, explicit labels, visible focus states, live conversation/error regions, reduced-motion styling and collapsible source cards.
- **Backend:** FastAPI, Pydantic schemas, a single explicit session state machine: `setup → mission → chat → debrief → chat (targeted retry)`; deletion is allowed from every phase. Actions in the wrong phase return 409.
- **RAG:** LangChain loaders, `RecursiveCharacterTextSplitter`, local deterministic 512-dimensional hashed word embeddings through LangChain’s `Embeddings`, and `InMemoryVectorStore`. Retrieval is lexical with a small English/German/Spanish alias map, keeping demo and live embeddings local. Top three chunks are retrieved per role-play turn. It is not a pretrained semantic embedding model; cross-language retrieval is limited.
- **State:** random bearer session IDs, per-session vector store, role/scenario, language/level, mission, turns, hints and goal evidence; no database, accounts, localStorage, persistent checkpointing or long-term memory. Calls to a session are serialized for chat and finish.

## Privacy and trust boundaries

Documents are processed **on the server**, not just on the device. Upload multipart parsing may temporarily spool larger files to the OS temporary directory; the upload is closed and its temporary backing file removed immediately after parsing. Extracted text, vectors and conversation state remain in process memory. Nothing intentionally saves them to disk, logs or browser storage. API responses use `Cache-Control: no-store`; LangChain tracing is disabled. Do not enable request-body logging or proxy caching.

**End & delete session** deletes server references and clears visible client data. Closing the tab attempts best-effort deletion with a keepalive request. Browser crashes/offline closes cannot guarantee that request; abandoned sessions expire after one hour of inactivity and a cleanup task runs every 30 seconds. Expiry also occurs before every action. Restarting the single backend process clears all sessions. Process memory deletion is reference deletion, not cryptographic zeroization. Local browser/OS memory and external provider retention are outside this app’s control.

In live mode, retrieved passages and conversation data are sent to OpenAI; provider handling is subject to your account’s policies. This notice appears before starting. Keys never reach the browser. Demo makes no external model calls. Google Fonts is used for typography; it is a third-party font request and receives no document or conversation text.

Uploaded text is untrusted data, never executable instructions. It is passed separately under `retrieved_passages` and described as untrusted in live system prompts. React escapes displayed text. Only the fixed retrieval/hint/mission functions are exposed by the application. There are no shell, web browsing, or arbitrary tool capabilities. Prompt injection and hallucination are reduced, not eliminated; citation-ID checking alone does not prove entailment. Use the evaluation plan before any public rollout.

## Verification

```powershell
python -m unittest backend.test_app -v
npm run build
```

Tests exercise all 36 scenario/conversation-language/feedback-language combinations, the full demo flow, evidence locations, mission editing, hints, debrief, retry, deletion, session isolation, expiry, phase guards, upload validation, DOCX parsing and untrusted document text. See [EVALUATION.md](EVALUATION.md) for quality evaluation and live-model release gates.

## Known limitations

English, German and Spanish only; interface labels remain English. Text chat only. The demo is intentionally scripted and its keyword rules can misclassify achievement. No OCR, legacy DOC files, speech, authentication, history, distributed sessions, semantic embeddings or analytics. Retry focuses only on the selected missed goal and replaces the previous scene’s turns/debrief. Model feedback and goal detection need human review. Live citation checks validate IDs, not factual entailment. Do not expose this unauthenticated prototype directly to the public internet: add transport security, deployment origin configuration, appropriate parser isolation, abuse controls and model cost limits first. Current limits include 100 active sessions, 30 learner turns per scene, 30 hints per session and one-hour idle expiry.
