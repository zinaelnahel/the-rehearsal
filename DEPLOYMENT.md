# Vercel deployment

## Current multimodal deployment

See [the implementation and activation guide](docs/MULTIMODAL.md). The source now
includes speech, a tool-calling agent, LangSmith synthetic evaluation and Chroma.
Revision 0.7 is deployed on the existing Vercel and Render services. See
[SUBMISSION.md](SUBMISSION.md) for evidence and remaining validation limits. `render.yaml` preserves a free-host memory fallback; optional
`render-persistent.yaml` prepares paid compute and a persistent volume without
applying them. Durable hosted retrieval requires that volume and a verified
`CHROMA_PATH`. Do not apply both Blueprints to the same service independently.

Docker includes FFmpeg. Enable `SPEECH_ENABLED=true` to expose microphone,
audio/video transcription and AI playback. Audio requires per-use consent and
server provider credentials. Live agent preparation is enabled by default; it
adds up to two provider calls per learner turn.

Create a GitHub `evaluation` environment with `LANGSMITH_API_KEY` and, for paid
evaluation, `OPENAI_API_KEY`. The new manual LangSmith workflow uploads only the
bundled fictional fixtures. Release now defaults to checking for a successful
LangSmith evaluation workflow on the same commit as well as CI; this can be a
demo experiment. Explicitly disabling that release input bypasses that gate.
Two hosted synthetic LangSmith experiments are recorded in SUBMISSION.md;
the updated GitHub evaluation workflow has not yet executed.

## GitHub Actions CI and release preparation

`.github/workflows/ci.yml` runs on pull requests, pushes to `main`, and manual
requests. Independent jobs run the Python tests and offline RAG benchmark,
build the Next.js frontend with Node 22, and build the backend Docker image.
The synthetic RAG report is retained as an artifact for 14 days. CI receives no
provider credentials and does not run paid live evaluations.

`.github/workflows/release.yml` is a separate manual release workflow, restricted
to `main`. It requires a successful push CI run for the selected commit and checks
that `main` has not advanced before requesting deployments. Releases are serialized.
It uses the existing services; it does not create hosting resources.

To activate after committing and pushing the workflow and evaluation files:

1. In GitHub repository settings, create an environment named `production`.
   Restrict deployment branches to `main` and optionally configure reviewers.
2. Add environment secrets `RENDER_DEPLOY_HOOK` and `VERCEL_DEPLOY_HOOK`.
   Copy the Render URL from the existing service's Settings / Deploy Hook.
   Create the Vercel hook for `main` in Project Settings / Git / Deploy Hooks.
   Treat both URLs as credentials; never commit them. Provider and proxy keys
   remain in their existing hosting settings, not GitHub Actions.
3. Keep Render automatic deployment disabled. Check Vercel's Git integration:
   automatic production deployments, if enabled, run independently of this gate.
   Disable that production path in the hosting configuration if all production
   releases must go through this workflow; preview deployments can remain separate.
4. Configure branch protection for `main` to require `Backend tests and RAG
   evaluation`, `Frontend build`, and `Backend Docker build` before merging.
5. After CI passes on `main`, open Actions / Release / Run workflow, selecting
   `main`. Inspect both hosting dashboards for completed builds, then follow
   the production verification checklist below.

Render receives the tested commit SHA. Vercel hooks deploy the latest commit on
their configured branch: avoid merging while a release request is being made.
This hook-based release is not an atomic, SHA-pinned deployment of both services.
Successful workflow completion means both deployment requests were accepted,
not that either build has finished or production is healthy. A partial failure
can leave one service updated; inspect the dashboards before rerunning. Backend
deployment clears in-memory rehearsals. No automatic rollback is implemented.

Workflow setup references: [GitHub Actions syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax),
[Render deploy hooks](https://render.com/docs/deploy-hooks), and
[Vercel deploy hooks](https://vercel.com/docs/deploy-hooks).

## Published deployment

- Frontend: https://the-rehearsal-lab.vercel.app
- Backend: https://the-rehearsal-api.onrender.com
- Source: https://github.com/zinaelnahel/the-rehearsal (`main`, public with user approval)
- Render service ID: `srv-dbkahtvlk1mc73bbdfk0`
- Vercel project: existing linked `zina3/the-rehearsal`; reuse `.vercel/project.json`.

Revision 0.7 is deployed in **live AI mode**, with speech and the agent enabled and memory retrieval, using the existing projects and production settings. It includes whole-dialogue review ratings, a collapsed optional plan map, context safeguards and small original production icons. The navigation/download follow-up adds reached-step navigation, explicit restart protection, continuing a reviewed scene and browser-only text downloads. The existing Nathan Fielder image, source credit and disclaimer remain in place. The difficult-conversation sample is now **Saying no to family**, with aligned English/German/Spanish notes and scripted boundary practice; custom contexts and final-breakup handling remain separate. Render retains the provider key and shared proxy secret; Vercel retains only `BACKEND_URL` and `API_PROXY_TOKEN`.

Historical revision 0.6 verification: the application changes were pushed in `7fb5c65`; the production-icon follow-up is recorded in Git history. Verification: 49 deterministic backend tests, a production frontend build and a 27-call fictional live smoke run across English, German and Spanish. The hosted Chrome check passed the live conversation, original image, keyboard-operated collapsed map, no sidebar map or per-turn ratings, whole-dialogue rating with optional reason/change/clear, mobile overflow, replay and verified deletion. Automatic Render deployment remains off; backend releases are triggered explicitly. Provider request ceilings remain ephemeral application limits, not billing limits.

The Render API key remains in ignored local `.env` for deployment management. GitHub CLI sign-in is configured locally. Never print credentials. There is no persistent session database: free-host sleeping, restarting or redeploying clears active rehearsals. Automatic Render redeployment is currently disabled; a source push alone does not rebuild the backend.

The supported initial deployment is **Next.js on Vercel + one FastAPI instance on a container host**. All-in-one Vercel deployment requires redesigning session storage first: process-local sessions cannot reliably survive serverless instance changes. This repository does not deploy an unreliable in-memory Python function on Vercel.

## Backend

1. Push the source to a repository you control. `.env`, `.runtime` and build outputs must stay excluded.
2. Create a Docker web service on Render (or an equivalent container host), using the repository's root `Dockerfile`. `render.yaml` provides a single-instance free-plan Blueprint; it asks for secrets rather than embedding them. Free-plan idle shutdown resets in-memory sessions.
3. Run **one instance and one Uvicorn worker**. Set the health check to `/health`. Do not attach a persistent disk.
4. Set these server environment variables in the host dashboard:
   - `REHEARSAL_MODE=live` (or `demo` until ready)
   - `OPENAI_API_KEY`: your provider key
   - `OPENAI_MODEL=gpt-4.1-mini`
   - `API_PROXY_TOKEN`: a strong random secret, shared only with the frontend server
5. Deploy and retain the HTTPS service URL. `/health` is public and returns no private data. All `/api/` routes require the proxy token when configured.

Generate a proxy secret locally with `python -c "import secrets; print(secrets.token_urlsafe(48))"`, then enter it directly in both dashboards. Do not commit it or paste it into chat. Keep the service to one instance. Restarts, redeploys and host sleep clear active rehearsals; users must start again. A host with idle shutdown can also cause initial cold-start delays.

## Frontend on Vercel

Import this repository as a **Next.js** project, with the repository root as its root directory. Alternatively, run `vercel` from this directory after signing in. `npm ci` and `npm run build` are supported. The backend and samples are excluded from the frontend CLI upload by `.vercelignore`.

Set these **server-only** Vercel environment variables for each environment being deployed:

| Variable | Value |
| --- | --- |
| `BACKEND_URL` | Backend HTTPS URL, without `/api` |
| `API_PROXY_TOKEN` | The exact same secret as the backend |

Do **not** add the OpenAI key to frontend code or a `NEXT_PUBLIC_*` variable. The key is needed only by the Python host. The server route `app/api/[...path]/route.js` forwards API requests and injects the backend token. It refuses a Vercel deployment with missing backend settings. Cross-origin browser mutations are rejected. This proxy token protects direct access to the backend; it does not authenticate people visiting the frontend.

Start with a protected Vercel preview and retain deployment protection for a class demo. Public access to a live-model app allows visitors to spend the provider budget; use account-level spend limits and add appropriate visitor access controls before opening it more broadly. No end-user accounts are added by this implementation.

## Verify before sharing

1. `/api/config` reports the intended mode.
2. Complete a sample rehearsal in each language, checking source passages, hints, debrief and retry.
3. Upload a PDF/DOCX under **4 MB**. This limit leaves room for multipart encoding below Vercel's function payload cap.
4. Delete a session; subsequent actions must return 404.
5. Direct calls to the backend `/api/config` without the proxy token must return 401, while `/health` remains 200.
6. Confirm neither uploaded text, conversation contents, keys nor proxy secrets appear in host logs or frontend bundles.

Run `python -m unittest backend.test_app -v` and `npm run build` before deployment. The Docker image has not been verified unless Docker is available in the build environment. API keys are loaded from runtime settings; uploading a local `.env` is never part of deployment.

## Role-play validation patch 0.6.1

The model-facing contract now uses required goal-assessment slots bound by the server, removing free goal/answer ID generation. Exact quotation and independent evidence checks remain in force. `/api/config` reports `roleplay_revision: 0.6.1`; partner response version identifiers use `roleplay-0.6.1`. The frontend API shape is unchanged. The patch passed 49 deterministic tests, the eight-fresh-take rent regression (40 calls), and the existing multilingual regression (27 calls). Reports use fictional samples only. Backend deployment remains explicit because Render auto-deploy is off; updating the backend restarts session-only state.


## Production hardening update (5 November 2026)

Read [current implementation and release evidence](docs/RELEASE_GATES.md) before
rolling out these changes. Docker now requires a proxy token and Linux parser
sandboxing; unsupported kernels reject file imports with a text fallback. CI
runs the confinement probe. Configure the persistent provider reservation ledger
at `/home/rehearsal/data/provider-budget.sqlite3`; the free plan cannot preserve
it across host replacement. Provider billing controls are separate.

The manual release workflow now also requires current live benchmark outputs and
attributed human reviews; it rescales neither missing reviews nor offline demo
scores into passes. Existing LangSmith and successful-CI checks still apply.
This update was deployed on 5 November 2026 at commit `f00d479` after the user explicitly requested a public-demo release with human review still pending. Both hosts are live. [Hosted checks](evaluation/hardening-hosted-2026-11-05.json) passed; the strict automated quality-release gate remains in place for future qualified releases.
