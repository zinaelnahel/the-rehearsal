# Optional native-caption fallback

Add `SUPADATA_API_KEY` to the ignored local `.env` to enable the fallback locally.
For production, set the same backend-only variable on the existing Render
service and deploy. It must never be a `NEXT_PUBLIC_` value or be set on the
frontend. Leaving it empty preserves the direct YouTube importer.

The direct importer runs first. On a blocked/failed read, the configured service
gets one request to the fixed `https://api.supadata.ai/v1/transcript` endpoint:

- `mode=native`: existing captions only; never `auto` or `generate`.
- `text=false`: timestamped chunks. Milliseconds are converted to seconds and
  passed through the existing ordered-segment and transcript-size validators.
- `chunkSize=50`: request small caption chunks for precise source citations.
  Each returned caption retains its own start and end; nearby captions are not
  merged. Timing precision depends on the source captions. Previously imported
  transcripts need to be imported again to get the smaller blocks.
- `lang`: the selected language. Different-language returns are rejected rather
  than silently substituting another language.

Supadata may return existing YouTube auto-captions. Native mode prevents
Supadata-generated transcription; it does not establish human caption authorship.
The response is labeled as retrieved through Supadata with unverified authorship.
The user still reviews and confirms the transcript before it becomes evidence.
The video URL is sent to this additional provider after the visible processing
notice/consent. Normal downstream live-model processing remains separate.

No additional SDK is required. The request uses HTTPS with certificate validation,
no environment proxy, no redirects, no automatic retry, a bounded response body
and the remaining import deadline. Credential/quota failures, missing captions,
unexpected async responses, malformed timestamps and language mismatches produce
actionable sanitized errors and retain the pasted-transcript alternative. This
native-only integration does not poll or retry asynchronous jobs.

The existing video-import request allowance applies. Supadata's account quota
also applies; the application does not enable paid plans or auto-recharge.
Native requests, including some unavailable-transcript responses, can consume
credits. Current service behavior and costs are documented at
[Supadata transcript API](https://docs.supadata.ai/get-transcript) and
[pricing](https://supadata.ai/pricing); a free tier is not unlimited production use.

Verification: 102 backend tests and the frontend production build pass. Fixture
tests cover native-only parameters, timestamp conversion, direct-success/no-key
paths, language checks and sanitized failures. Two real native requests with the
configured key succeeded on 4 November 2026: `EvEsWpiT8WQ` yielded 29 grouped
review blocks / 55,781 characters; `01-59MEwE9Q` yielded four blocks / 7,700
characters. Group counts differ from the direct importer because provider chunk
sizes differ. No transcript text or credentials are stored in the
[metadata-only report](../evaluation/supadata-native-check-2026-11-04.json).
These were two native-caption requests, not AI-generated transcripts. The backend secret was subsequently configured on Render and source commit
`43ea04075097196cb4325a2b833b65f093f5f20b` deployed. Both links then passed
through the public app with `source_method=youtube_captions_supadata`, matching
the local group/character counts and requiring transcript confirmation. See
the [metadata-only hosted report](../evaluation/supadata-hosted-check-2026-11-04.json).
These are successful checks of two links, not a guarantee for every video or
future provider availability. Native-caption service credits were used; no
Supadata AI generation or OpenAI calls were made in these caption checks.
