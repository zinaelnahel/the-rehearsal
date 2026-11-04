# Submission verification — 4 November 2026

The four concerns supplied in the conversation have executable implementations
and current local/live-provider evidence. Public release checks, exact source
commit and deployment IDs are recorded in the [v0.7.0 release](https://github.com/zinaelnahel/the-rehearsal/releases/tag/v0.7.0).
The selected free hosting uses in-memory retrieval; persistent Chroma is explicitly
demonstrated locally. This is not a claim of hosted vector persistence.

| Requirement | Verified evidence | Practical limit |
| --- | --- | --- |
| Text plus audio/speech | [Real EN/DE/ES TTS → Whisper checks](evaluation/submission-speech-2026-11-04.json), including MP4 audio extraction; [real browser speech flow](evaluation/submission-browser-speech-2026-11-04.json) | Three TTS-generated fixtures, not a human speech benchmark. Normalized word error rate was 0 for these fixtures only. Browser microphone input used a synthetic WAV through Chrome's fake device; provider calls were real. |
| LangSmith testing/evaluation | [Hosted RAG experiment export](evaluation/submission-langsmith-rag-2026-11-04.json), [hosted tool experiment export](evaluation/submission-langsmith-tools-2026-11-04.json), [trace audit](evaluation/submission-langsmith-traces-2026-11-04.json) | Fictional fixtures only. The application runs on Vercel/Render; a LangSmith evaluation gate is implemented for releases, but the updated GitHub workflow has not yet executed. This is not a claim of LangSmith application hosting. |
| Agent with several tools | [Real model selections](evaluation/submission-agent-tools-2026-11-04.json): retrieval, mission progress and guidance each selected the corresponding tool; exact-quote checking is a fourth available tool | Three bounded preparation probes. The separate nine-case real role-play benchmark exercised retrieval and mandatory answer validation. Tools cannot write session state. |
| Persistent vector database | Chroma-backed [live RAG benchmark](evaluation/submission-live-rag-2026-11-04.json), cross-process read, expiry and restart-deletion tests in [backend/test_multimodal.py](backend/test_multimodal.py) | Verified on local disk. The existing public Render service is free and has no persistent volume; hosted durability is still pending. Embeddings remain the documented local hashed baseline. |

The nine-case real RAG benchmark passed all deterministic checks and all four
model judges (correctness, relevance, groundedness, retrieval relevance), using
81 provider calls. Each judge dimension passed 9/9. Required-value checks apply
to six answerable cases and passed 6/6; the other three intentionally require an
unknown answer. The original report's aggregate required-value denominator counts
the nonapplicable cases; the reporter has been corrected for subsequent runs.
Judges use the same configured model as generation and are not human ground truth.

Current local verification also includes 80 passing backend tests, the Next.js
production build, source-selection/browser regressions, actual FFmpeg decoding,
and Render Blueprint JSON Schema validation. Docker is unavailable locally;
the updated container build must be verified in GitHub CI or hosting.

## Hosted LangSmith experiments

- [RAG: nine cases plus four judges](https://smith.langchain.com/o/68448f7b-c77e-45a7-bae0-7e331e58d545/datasets/b37aba08-aee5-4070-ac88-cd845c58106e/compare?selectedSessions=4bf850ca-718c-4603-a5c3-f4d81f879968)
- [Tool selection: three cases](https://smith.langchain.com/o/68448f7b-c77e-45a7-bae0-7e331e58d545/datasets/8ce9124d-4edc-4442-bf1d-f54164e96fd5/compare?selectedSessions=87721216-b5db-49c0-8aa0-8ad7db89c063)

These links may require access to the owner's LangSmith workspace. The exported
reports above provide reviewable results without requiring that access. Ordinary
user sessions remain untraced, even when tracing environment flags are set.

## Reproduce locally

```powershell
python -m pip install -r backend/requirements.txt
python -m unittest discover -s backend -t . -p 'test_*.py' -v
python scripts/evaluate_rag.py
npm ci
npm run build
```

Explicit paid verification, using only fictional fixtures and server credentials:

```powershell
python scripts/evaluate_rag.py --live --judge
python scripts/evaluate_speech.py
python scripts/evaluate_agent_tools.py
python scripts/evaluate_langsmith.py --live --judge
python scripts/evaluate_langsmith.py --suite tools --live
```

Set `VECTOR_STORE=chroma` and a writable `CHROMA_PATH` to reproduce database
evidence. The speech runner enables speech for its own synthetic test context.
LangSmith requires `LANGSMITH_API_KEY`; all paid checks require `OPENAI_API_KEY`.
No real learner audio, documents or conversations are used in these reports.

## Demonstration sequence

1. Start the backend with `SPEECH_ENABLED=true`, `VECTOR_STORE=chroma`,
   `REHEARSAL_AGENT_ENABLED=true` and `REHEARSAL_MODE=live`; start the frontend.
2. Show the three source tabs: sample, situation (text/document/optional listing)
   and audio/video (record/upload/link). Use only fictional source material.
3. Record or upload speech, show the editable transcript, and press Send explicitly.
   Show the source-backed answer, separate goal/answer states and AI voice playback.
4. Open the two LangSmith experiments and inspect model/tool/retrieval/evidence
   spans. Show different selected tools in the tool experiment.
5. Run the persistence tests to demonstrate retrieval from a second process,
   session isolation, expiry and explicit deletion after restart. Conversations
   themselves remain in memory and do not resume after restart.
6. End/delete the session and show that subsequent status access returns 404.

## Remaining hosted release gates

1. Publish the reviewed source and synthetic evidence to the existing repository.
2. Inspect passing GitHub CI, including the actual Docker build.
3. Configure the GitHub `evaluation` environment and run its LangSmith workflow
   for the exact release commit. Keep keys in secret storage, never in source.
4. Review/authorize paid Render compute and a 1 GB persistent disk using
   [render-persistent.yaml](render-persistent.yaml), or keep the demonstration local.
   The free-host fallback is not hosted persistence evidence.
5. Deploy the exact revision to Render and the existing Vercel frontend. Verify
   speech/agent/Chroma capabilities, real end-to-end behavior, proxy protection,
   disk write permission and retrieval surviving a controlled backend restart.
6. Export the release evidence and update this page with commit/build/deploy IDs.

The supplied requirement wording mentions LangSmith for deployment. The current
design uses LangSmith evaluation as a gate before Vercel/Render deployment. If the
assessor literally requires the agent to be hosted on LangSmith Deployment, that
is a separate hosting requirement and must not be claimed from this architecture.
