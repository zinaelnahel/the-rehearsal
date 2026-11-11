# A short live demo

Use the Spanish flat-viewing sample for a two-minute walkthrough:

1. Review the prepared captions and confirm them. Keep Spanish conversation,
   B2 style and English feedback. Build the mission.
2. Keep one goal: **Ask about the monthly rent and included bills for the flat
   being viewed**. Remove the other goals, then start.
3. Send: **¿Cuánto cuesta el alquiler al mes y qué gastos están incluidos?**
4. Check that the reply gives an upper bound of less than €1,000 and includes
   gas and water, with citations to this flat's caption segments. The video
   discusses several flats; do not transfer facts between them or present it as
   a currently available listing.
5. Finish and show feedback quoting the learner's actual question.

## If the network or provider is slow

The UI shows elapsed waiting time. Server-side turns have a 40-second wall-clock
allowance, inside the proxy's 55-second window. The browser's 65-second deadline
covers receiving the complete response body too. Timed-out turns do not append
a conversation message. Optional agent planning can fall back to the initial
retrieval; evidence and partner-role checks remain required.

After an uncertain network result, choose **Check rehearsal**. It reads the
authoritative saved conversation. **Retry same message** reuses the request ID;
concurrent or repeated submissions return the original result instead of adding
another turn. Do not refresh away from an active rehearsal just to recover.

If the provider cannot complete the demo, use the screenshots from the latest
successful real run, say when they were recorded, and clearly identify them as
a fallback rather than a live response. Never describe mocked browser tests as
proof that a provider-backed conversation completes.

Recorded fallback (November 11, 2026, local app with the real AI provider):
[plan](demo/plan.png), [cited reply](demo/reply.png), [review](demo/review.png).
The [run record](../evaluation/live-apartment-deadline-2026-11-11.json) binds the
backend and API-client source hashes to the measured run: 5.6 seconds for the
mission, 5.3 seconds for the reply, and 1.9 seconds for review. These screenshots
show a recorded local run, not a live production response.

## Repeat the real check and create fallback screenshots

Start the app locally with a live backend, or explicitly target production:

```powershell
$env:LIVE_DEMO_URL='https://the-rehearsal-lab.vercel.app'
$env:CHROME_PATH='C:\Program Files\Google\Chrome\Application\chrome.exe'
node scripts/test_live_apartment_browser.mjs
```

This calls the real provider. It records request timings, cited reply and build
identities in `.runtime/live-demo-report.json`, and plan/reply/review screenshots
in `.runtime/live-demo/`. It deletes its synthetic session afterward. The separate
`test_turn_recovery_browser.mjs` intentionally simulates a lost response; its
results concern UI recovery, not model quality.

## Explain the evaluation honestly

Present benchmark scores as **author-authored synthetic regression results**.
Specify the dataset, model, build and date. They detect regressions in known
cases; they do not establish general accuracy, safety or performance for arbitrary
recordings or situations. The labels have not been independently human-reviewed.
Mention remaining goal-detection errors and distinguish these historical dataset
results from the small provider-backed demonstration and simulated UI checks.
