# Implementation and release evidence — 5 November 2026

Delivered:

- Shared and per-client request throttling; concurrency control; deletion stays available.
- Persistent atomic daily provider reservations, including failed calls and paid captions; input/output ceilings.
- Disposable PDF/DOCX workers with resource/time limits, two parser slots, filtered secrets, Linux Landlock/seccomp policy and a mandatory container CI probe. Public configuration requires a proxy secret and sandbox policy. Unsupported confinement rejects uploads with a paste-text alternative.
- Video URLs, pasted text and consent survive language changes. Old-language results and confirmations clear with an explanation; wrong-language captions are rejected. Audio confirmations also need review after language changes.
- Independent EN/DE/ES interface language, localized controls, privacy/consent copy, errors and accessible labels. User/source/model text retains its original language.
- Desktop Chromium source-to-deletion journeys in all three locales. PDF/DOCX file-chooser uploads use the real parser. Real MediaRecorder uses a synthetic microphone and a stubbed transcription response.
- Real FFmpeg decoding for WAV, MP3, M4A, OGG, WebM, MOV and MP4. Document rejection tests include scans, encryption, malformed files, page limits, oversized uploads and expanded-DOCX limits. Low-confidence transcription rejection uses synthetic provider metadata.
- A 126-case synthetic benchmark across EN/DE/ES and Everyday/B1/B2, with feedback and safety outputs. Missing human verdicts never count as passes.
- Offline human-review worksheet, output-bound reviews, and a production gate rejecting missing reviews, stale code/data, weak feedback scores and unacceptable safety behavior.

Final backend verification: **114 tests passed**; production frontend build passed.

Browser evidence: [recorded checks](../evaluation/browser-release-2026-11-05.json).
Quality evidence: [offline report](../evaluation/quality-release-2026-11-05.json).
All 126 offline cases completed; all 18 safety cases paused without provider calls
or graded coaching. No feedback quote was invented. Scripted-demo reference-status
accuracy is only 38.1%: an exposed limitation, not proof of production quality.
Human coverage is zero.

## Reproduce and review

```powershell
python -m unittest discover -s backend -t . -p 'test_*.py' -v
npm run build
python scripts/evaluate_quality.py --dataset evaluation/quality-release-dataset.json --output .runtime/release-quality.json
python scripts/export_quality_review.py .runtime/release-quality.json --output .runtime/quality-human-review.html
```

The offline worksheet shows full sources, turns, answers, feedback and safety.
Reviewers enter their identifier, grounding/answer/goal verdicts, feedback
usefulness (1–5), safety appropriateness and an explanation, then download JSON.
It sends nothing and does not autosave. Use fluent human reviewers and adjudicate
disagreements. Model verdicts and empty worksheets are not human-reviewed evidence.

For a paid live release benchmark, explicitly run:

```powershell
python scripts/evaluate_quality.py --live --dataset evaluation/quality-release-dataset.json --output evaluation/quality-release-live.json
python scripts/export_quality_review.py evaluation/quality-release-live.json --output .runtime/quality-human-review.html
```

This uses the configured provider key and incurs charges. Plan the hourly call
allowance and daily reservation budget; keep provider billing limits in place.
Runs hitting an allowance are incomplete. Save attributed reviews as
`evaluation/quality-release-live.review.json`, then score:

```powershell
python scripts/evaluate_quality.py --score-report evaluation/quality-release-live.json --reviews evaluation/quality-release-live.review.json --output .runtime/release-reviewed.json --require-human
python scripts/check_review_provenance.py .runtime/release-reviewed.json
```

Release runs these checks before deploy hooks. Passing requires three languages
and styles, safety cases, complete human verdicts, accepted grounding/answer/goal/
safety behavior, usefulness at least 4/5, valid feedback/safety contracts and current
code/dataset hashes. A finite benchmark cannot guarantee general reliability.

For browser checks, install Playwright, run `python scripts/create_media_fixtures.py` to create fictional document fixtures, start the demo backend/frontend, and run
`node scripts/check_browser_release.mjs`. `REHEARSAL_TEST_URL` defaults to
`http://127.0.0.1:3135`; set `CHROME_PATH` for system Chrome. The workspace's existing
Playwright install is also supported. No real provider calls are made by this harness.

## Deployment and external validation

Docker sets `PUBLIC_DEPLOYMENT=true` and `PARSER_SANDBOX=required`. Configure the
same `API_PROXY_TOKEN` on frontend/backend. Run the sandbox probe on compatible Linux:

```sh
docker build --tag rehearsal-ci .
docker run --rm --entrypoint python rehearsal-ci -m backend.sandbox_probe
```

The policy follows the [kernel API](https://docs.kernel.org/userspace-api/landlock.html).
Native Linux confinement was not executed on this Windows machine (Docker/WSL
unavailable); CI now requires the probe. Do not weaken it for an unsupported host;
use pasted text or a sandbox-capable host.

Configure `PROVIDER_DAILY_BUDGET_USD`, `PROVIDER_CALL_RESERVATION_USD` and
`PROVIDER_BUDGET_PATH`. Size reservations for your model, speech/caption prices and
byte/token ceilings. These are conservative reservations, not a provider billing
guarantee. The ledger needs durable storage to survive host replacement. Free
Render storage is ephemeral; the optional persistent deployment already mounts
`/home/rehearsal/data`. No paid plan was activated. Provider account spend limits
and alerts need account-side configuration. Edge DDoS protection remains the
host's responsibility. Per-client identity uses Vercel's
[overwritten IP header](https://vercel.com/docs/headers/request-headers), hashed
with the proxy secret and UTC date; application counters retain no raw IPs.

Physical iPhone/Safari and Android/Chrome tests still require those devices,
including denied permissions, interruptions, poor speech and camera media.
Viewport resizing and synthetic microphones are labeled accurately. Independent
human scoring requires real reviewers; none was invented. No production deployment
or provider billing setting was changed by this work.
