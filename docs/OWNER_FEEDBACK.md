# Private feedback report

The owner page is `/owner/feedback`. It requires HTTP Basic authentication:
username `owner`, password set by the server-only `FEEDBACK_OWNER_TOKEN`.
Use HTTPS outside localhost. The secret must be at least 32 characters and must
be configured identically on Vercel and Render. Never use `NEXT_PUBLIC_` for it.

The page shows whole-dialogue ratings, the six optional quality questions,
negative categories, individual-response totals and language breakdowns. It
offers JSON and standalone HTML downloads. These are aggregate report snapshots,
not raw feedback exports, SQLite backups or a persistent cloud database.

## Current storage limit

The free Render instance keeps SQLite on temporary storage. Redeploying or
replacing the backend can erase existing feedback. This page makes future
reports accessible without a paid Shell, but does not change that storage limit.
Save a downloaded report before future redeployments.

Deploying this feature also requires a backend redeploy. Because the existing
service has neither a report-reading endpoint nor free Shell access, this code
cannot retrieve the current temporary database before that deployment. Confirm
the possible loss of existing ratings before proceeding. Permanent automatic
collection requires a separately configured durable database or disk; this
implementation does not purchase or provision either.

## Access and privacy

The generated local credentials are in the ignored file
`.runtime/feedback-owner-credentials.json`. Local preview uses `.env.local`.
There is no public navigation link to the report. Share the URL and password
only with people who should see participant feedback. Basic credentials may
remain cached by the browser; use a private browser window on shared devices
and close it afterward.

The Next.js owner route checks credentials before fetching data. The backend
requires the separate owner header as well as its existing proxy protection.
The ordinary application proxy does not forward owner credentials. Responses
use `private, no-store`, `noindex`, `nosniff` and a restrictive CSP. Credentials
are never included in page HTML, exported reports or client JavaScript.

## Checks

```powershell
python -m unittest backend.test_owner_feedback backend.test_feedback -q
node --test scripts/test_owner_feedback.mjs
$env:CHROME_PATH='C:\Program Files\Google\Chrome\Application\chrome.exe'
$env:AXE_SCRIPT_PATH='.runtime/browser/axe.min.js'
node scripts/test_owner_feedback_browser.mjs
```

The browser check targets localhost only, reads aggregates without adding
feedback, verifies authentication and downloads, and audits mobile reflow and
accessibility. CSP is bypassed only in the audit browser to inject axe; the
actual response must still send the restrictive policy.
