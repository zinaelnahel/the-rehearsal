# Learning from real use

Visitors can give thumbs up/down and an optional category, including **Too slow**.
Ratings stay in session memory by default. An unchecked **Share my anonymous
rating to help improve the app** checkbox explicitly opts that rating into a
separate SQLite feedback store. This is product evaluation, not automatic model
training. No provider, analytics service or LangSmith receives the rating.

## What is saved

The shared record contains a random feedback receipt, UTC creation/update dates
(day only), rating/category, response-vs-dialogue kind, scenario, conversation
language/style, demo/live mode, configured model, frontend build (or `unknown`),
backend code fingerprint and response-contract version. Numeric snapshots include
turn count, goal/practised/confirmed/unresolved counts, withheld reply count and
successful server chat-turn timing totals/counts. The fingerprint works for local
uncommitted code; it is not presented as a release commit. Frontend revision values
are client-supplied and are useful grouping metadata, not attested provenance.

There are no session IDs, response IDs, IP addresses, user agents, contact details,
user-entered reasons, documents, goal text, conversations, hints, quotations,
audio or transcripts in the shared database. The server constructs an allowlisted
snapshot; extra request fields and arbitrary reason/build text are rejected.
No identity or unique-visitor tracking is introduced. Small metadata groups can
still be distinctive; keep the database and reports private.

Changing a shared rating updates the same row; retries do not create duplicates.
Unticking the checkbox withdraws the stored copy and keeps the session rating.
**Clear** removes both copies. A storage failure returns an error rather than
claiming sharing/removal succeeded. Visitors can withdraw while that feedback
control is accessible in the current scene; after leaving/replacing it or deleting
the session, the server discards the association and cannot identify the record
for later individual withdrawal. This limit appears in the consent notice.

Explicitly shared feedback survives session deletion and process restarts.
It expires after at most `FEEDBACK_RETENTION_DAYS` calendar days (default 90,
bounded to 1–365); creation date, not last edit, controls expiry. Startup, the
30-second cleanup task, writes and report generation purge expired rows. A stopped
server cannot run cleanup until it next starts. SQLite row removal is logical
deletion; host backups and exported reports have their own lifetimes.

## Owner report

Run from the project root, with the same `FEEDBACK_DB_PATH` used by the backend:

```powershell
python scripts/report_feedback.py --days 30 --html .runtime/feedback-report.html --json .runtime/feedback-report.json
```

Open `.runtime/feedback-report.html` to see whole-dialogue useful/unhelpful totals,
negative categories, mean successful server-turn latency and breakdowns by
scenario, language, style, mode, model and app version. Regenerate it after more
people use the app. Empty stores display **No shared ratings yet**; synthetic test
records are never added to the real database.

There is deliberately no public feedback-reading endpoint. Generate the report
on the backend host or from a private copy of its database. JSON contains aggregates
only, never receipts or raw rows. Keep reports outside `public/` and do not commit
the database or real feedback exports. To disable new sharing, set
`FEEDBACK_ENABLED=false`; visitors can still remove an existing shared copy while
their scene is accessible.

For this workspace's optional dependency cache, prepend
`$env:PYTHONPATH="$pwd/.runtime/python-deps"` if required by the Python installation.

## Reading the results

- Ratings measure perceived usefulness among people who opted in, not all users
  or unique people. Individual response ratings are counted separately, so they
  do not duplicate whole-dialogue performance totals. Multiple takes by the same
  visitor still count separately; no identity data is collected to deduplicate them.
- Mean latency uses successful chat-turn time after the session lock is acquired,
  including retrieval, agent preparation and evidence checks. It excludes speech,
  client/network/queue time and failed requests. It is not end-to-end voice latency,
  a failure-rate metric or a p95. Repeated/continued takes can overlap; this is
  descriptive feedback, not a unique-traffic performance benchmark.
- A **Got a fact wrong** rating is an allegation to investigate, not a verified
  hallucination. Without text, the original interaction cannot be reconstructed.
- Investigate recurring categories using fictional cases. Add a regression fixture,
  make the change, rerun the existing evaluations, then compare matching cohorts
  across versions. Small samples, self-selection and differing scenarios make
  before/after percentages unreliable as evidence of causation.

## Storage and hosting

Local default: `.runtime/feedback.sqlite3`. Docker default:
`/home/rehearsal/data/feedback.sqlite3`. Configure `FEEDBACK_DB_PATH` on a durable
volume before relying on production collection. The current free backend host has
ephemeral storage: the file can disappear on redeploy or host replacement. This
implementation does not provision a paid volume or claim hosted durability.
The optional persistent hosting configuration mounts `/home/rehearsal/data`;
applying it and verifying backups/durability is a separate deployment step.
Changing the path does not migrate an old file. Database access is single-instance,
matching the existing session architecture.

`backend/test_feedback.py` verifies explicit opt-in, text/ID exclusion, cross-session
access, updates/withdrawal/clear, failures, restart-independent reporting and expiry.
