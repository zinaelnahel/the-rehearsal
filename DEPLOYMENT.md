# Vercel deployment

## Reviewed media navigation and uploads — 9 November 2026

Commit `dc0cc54f25fd2faf358ba6f552e0d63c60e5d379` is live on both services.
[Release evidence](evaluation/deployment-media-navigation-2026-11-09.json)
records passing CI/security checks, 149 backend tests, 24 frontend tests and
successful public build-identity, health, access-protection and deletion checks.
Hosted Chrome checks with all API responses mocked verified edited transcript
and confirmation retention, rebuilding without reimport, clearing on deletion,
and the missing-microphone message. A separate local test passed a synthetic WAV
through the actual browser/Next/FastAPI/FFmpeg path with a stubbed provider.
No paid provider calls were made. Real-device capture and real-provider
transcription remain unverified; the original hosted upload-network error was
not reproduced. The user explicitly requested push and manual redeployment;
independent human-reviewed live release evidence remains missing.
See [media verification](docs/MEDIA_RETEST.md).

## Engineering update — 9 November 2026

Commit `83b4cbdc08fe3c17c02f905f9104cea133313845` is live on both services.
[Release evidence](evaluation/deployment-engineering-update-2026-11-09.json)
records successful CI and dependency security workflows, 149 offline backend
tests and passing public build-identity, health, access-protection and deletion
checks. The frontend was promoted after the backend became live. This deploy
updates the locked dependency stack, adds numeric session-local model usage
metrics, improves history trimming and strengthens evidence provenance. The
user requested manual redeployment; independent human-reviewed live evidence
is still missing. Hosted checks made no paid model calls. The four documented
Chroma exceptions and remaining engineering work are described in
[SECURITY.md](SECURITY.md) and [the engineering review](docs/BEST_PRACTICES.md).

## Removal of automatic danger pauses — 9 November 2026

Commit `a52270fd6805a52afabb56923ea8aafa9097c602` is live on both services.
[Release evidence](evaluation/deployment-no-danger-checks-2026-11-09.json) records
successful CI, 141 offline backend tests, 126 completed offline quality cases
and passing public build-identity, health, proxy-protection and deletion checks.
The user requested removal of application danger-keyword checks and forced
support-note pauses, then explicitly requested push and redeployment. Related
model pause instructions were removed. The 18 sensitive-context fixtures now
expect ordinary rehearsal rather than an automatic pause; human review is still
required by the release workflow. This was a user-requested manual release;
independent human-reviewed live evidence remains missing. Hosted checks made no
provider calls. The complete reported rental transcript also passed a local
source-to-review check without a pause. Start a fresh rehearsal for retesting.

## Pet-question tracking — 9 November 2026

Commit `d4ccddd75a05ed7e4f3405dfd964e869ccd8715a` is live on both services.
[Release evidence](evaluation/deployment-pet-tracking-2026-11-09.json) records
passing CI, 140 offline backend tests, frontend checks and public health,
build-identity, proxy-protection and session-deletion checks. Explicit pet-policy
questions have a bounded action-evidence backstop, including replay, without
confirming an unsupported answer. The German partner label is corrected.
The user approved a new one-time exception to the missing independent
human-reviewed live benchmark. The release gate remains unchanged. Hosted
verification made no model calls; broader live-model reliability and generation
latency are not established by these checks. Start a fresh take to test the fix;
historical saved reviews are not rescored.

## Family action scoring — 6 November 2026

Commit `6381135a97a6885ad97b9eefa1dd14cb9aa3f9a2` is live on both services.
[Release evidence](evaluation/deployment-family-scoring-2026-11-06.json) records
passing CI and public health/proxy/session checks. All 138 offline backend tests
passed. The exact two-message Spanish QA sequence was also checked locally with
the live model: progress 1/3 → 3/3 and final review 3/3, with verbatim evidence.
This is a narrow check, not a general scoring accuracy estimate. The user approved
a new one-time exception to the still-missing independent human-reviewed live
release report; the release workflow and production provider settings were not
changed. Public release verification made no model calls. Old browser-saved
reviews remain historical snapshots; start a fresh take to test the fix.

## Browser library and conversation pacing — 6 November 2026

Source commit `094065c307de4063abc8561cbf53548d743a8552` is live on both existing
services. [Release evidence](evaluation/deployment-library-pacing-2026-11-06.json)
records passing CI, hosted public checks and browser checks. This update adds the
optional on-device rehearsal library, one gentle follow-up before accepting a
repeated refusal/firm boundary, and removes the duplicate recorder from chat.
The user explicitly approved a new one-time manual release exception for this
commit; the previous release's exception was not reused. The workflow remains
unchanged. Hosted browser API responses were mocked and release verification made
no paid model calls. Production provider limits were not changed; the explicitly
disabled local daily ceiling remains a local setting. See
[library behavior and privacy](docs/REHEARSAL_LIBRARY.md).

## Voice, shared feedback and role checks — 6 November 2026

Source commit `551518cda41c185c404cee8d6f372fc13ca088be` is live on the existing
Render and Vercel services. [Deployment evidence](evaluation/deployment-voice-feedback-2026-11-06.json)
records the deploy IDs, successful GitHub CI, public health/proxy/config/session
checks, and hosted browser checks. The frontend was promoted after the backend
became live. No paid model calls were made during release verification; browser
speech/chat/feedback API responses were mocked. Live multilingual model behavior
and broad speech accuracy are not established by those checks.

The user explicitly authorized this one manual deployment as an exception to the
Release workflow's missing current, independently human-reviewed live evidence.
The workflow gate and provider allowance settings were left unchanged. This is
not a precedent or a standing approval to bypass the release workflow.

Voice uses a fixed 1.2-second pause. Shared feedback is opt-in, retained separately
for up to 90 days and exposed only through private owner reports. The existing
free backend still has ephemeral storage; durable feedback collection requires a
durable volume or store. No paid hosting upgrade was applied.

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


## Frontend identity and session-preserving UI releases

The footer now shows independent UI and API commit links. The old role-play
contract revision is no longer presented as the application build version.
For Vercel CLI releases, pass `REHEARSAL_BUILD_SHA` as a build variable and
`BACKEND_BUILD_SHA` as a runtime variable. Obtain the backend SHA from the live
Render deploy, not from the current Git branch. An unidentified build is displayed
as unidentified rather than guessed. A Vercel build without a valid frontend SHA
fails. The proxy also exposes these non-secret IDs in `/api/config`.

Example (replace both SHA placeholders with the verified full commits):

```powershell
vercel deploy --prod --yes --build-env REHEARSAL_BUILD_SHA=<frontend-sha> --env BACKEND_BUILD_SHA=<live-render-sha>
```

A frontend-only release does not restart Render or clear its in-memory sessions.
Keep an existing review tab open, or download its review before refreshing; a
refresh still invokes the app's existing best-effort page-close deletion behavior.
The selector regression can be repeated without creating any sessions:

```powershell
node scripts/check_language_selectors.mjs
```

Set `REHEARSAL_TEST_URL` and optionally `CHROME_PATH`/`EXPECTED_FRONTEND_SHA`.
The test checks nine interface/conversation combinations, feedback/style values,
the spelling of Español, URL/consent retention, actual caption request payloads,
build labels and mobile-width layout. Caption responses are explicit fixtures.


Frontend follow-up deployed on 5 November 2026: UI `0553f3a`, API `f00d479`.
The canonical selector values and Español spelling passed all nine language
combinations on the public URL. Footer commit links matched the verified deploys.
Fresh hosted PDF/DOCX imports and deletion passed. Render was not redeployed or
restarted, and the user's existing review session was not accessed. See
[the verification record](evaluation/language-selector-hosted-2026-11-05.json).
Real physical microphone and mobile-device testing are not claimed by this check.


Partner-role regression deployed on 5 November 2026: UI and API `1124913`.
After the user confirmed their open review was saved/finished, Render was
redeployed and Vercel published with matching build identities. CI and 118 offline
tests passed. The final local real-provider check covered EN/DE/ES family scenes
and a rent regression (30 calls); the hosted check repeated the reported English
wording, verified actual-turn feedback and deleted its own test session. No
independent human-review result is claimed. See
[hosted evidence](evaluation/family-roles-hosted-2026-11-05.json) and
[synthetic multilingual evidence](evaluation/family-roles-live-2026-11-05.json).
