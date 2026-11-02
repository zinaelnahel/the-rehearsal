# Vercel deployment

## Published deployment

- Frontend: https://the-rehearsal-lab.vercel.app
- Backend: https://the-rehearsal-api.onrender.com
- Source: https://github.com/zinaelnahel/the-rehearsal (`main`, public with user approval)
- Render service ID: `srv-dbkahtvlk1mc73bbdfk0`
- Vercel project: existing linked `zina3/the-rehearsal`; reuse `.vercel/project.json`.

The previous revision 0.5 deployment ran in **live AI mode**. Revision 0.6 reuses these existing projects and production settings; its source includes whole-dialogue review ratings, optional plan maps and context safeguards. The user confirmed key rotation; the configured replacement key passed real-provider tests and is stored on the Python host only. Render has `REHEARSAL_MODE=live`, `OPENAI_MODEL=gpt-4.1-mini`, `MODEL_CALLS_PER_HOUR=200`, the provider key and shared proxy secret. Vercel has only `BACKEND_URL` and `API_PROXY_TOKEN`; neither the source nor browser bundles contained configured credentials in the release scan.

The release’s code commit is `d6b6fbd`. Local contract tests: 29 passed. The final real-provider smoke run used 27 calls across three languages. The production Chrome run verified the live listing/pasted-text flow, custom-goal question, supplied-phrase translation, mission/sidebar branching maps, mobile readability, replay and deletion. The hosted public Idealista read returned 424 with an explicit fallback, not a successful import. Old demo clients are rejected at live mission creation until they refresh and display the updated processing notice. The global model-call ceiling and per-session ceiling are ephemeral request caps, not provider billing limits.

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
