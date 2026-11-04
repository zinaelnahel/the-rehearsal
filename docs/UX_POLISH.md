# Connection and review polish

The setup workflow and model/evidence pipeline are unchanged.

- The existing `/api/config` request begins on page load. An immediate connection
  panel becomes a slow-connection message after eight seconds, without promising
  a wake-up duration. A bounded failed request offers explicit retry; no extra
  health ping, scheduled keep-warm job or automatic mutation retry is added.
- Users can read the selected fictional sample locally while waiting. This
  display does not create a session or send their source/conversation. Refresh
  `app/sample-previews.json` with `python scripts/generate_sample_previews.py`
  after changing the server sample files.
- Demo chat has an optional explanation of scripted replies and approximate goal
  matching. It is shown only when config reports demo mode.
- The review retains separate counts for learner actions and confirmed answers.
  One next-step card prioritizes unknown/unverified answers, then missed learner
  actions. The existing replay-replacement confirmation remains in place.
  Alternate goals are a collapsed secondary disclosure. Completed goals receive
  a completion message rather than a claim that all real-world outcomes are known.

Verification: production build and browser checks cover immediate/slow/failed
connection, explicit retry, local sample reading, preserved form values,
unconfirmed-answer priority, replay cancellation/acceptance, completed goals,
keyboard disclosure controls, 390/1280px horizontal overflow and session deletion.
Connection responses and the completed-goal debrief are UI fixtures; the other
rehearsal requests use the real local demo backend. No provider calls, hosted
rollout, moderated usability study or full screen-reader audit is claimed.
