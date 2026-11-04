# Blocked YouTube caption requests

On 4 November 2026, `01-59MEwE9Q` returned 35 English caption segments through
the local importer, but the deployed service returned HTTP 424. This confirms a
hosting-dependent failure, not proof that the video lacks captions. The caption
library [documents cloud-provider IP blocking](https://github.com/jdepoix/youtube-transcript-api#working-around-ip-bans-requestblocked-or-ipblocked-exception).
We did not establish the exact underlying hosted HTTP status for that request.

Automatic imports are still attempted. YouTube HTTP 403/429 responses now explain
that the server request was rejected and the video may still play in a browser.
This is an error/recovery improvement, not a bypass or guarantee of hosted access.
No proxy service, user-cookie transfer or external transcript provider is added.

The same video-link panel offers **Have the transcript? Paste it here** and opens
it after import failure. The user can copy an available transcript from YouTube,
paste it, review it and explicitly confirm it. The existing mission action sends
the confirmed text and reference link to the backend. Editing text or switching
sources invalidates confirmation. The backend rejects mixed sources, missing
confirmation, empty text and unsafe reference URL forms.

Pasted text is labeled **User-pasted transcript (not fetched from video)**.
Citations use source sections, not fabricated timestamps. The video URL is a
user-supplied reference, not evidence that its contents were independently fetched
or checked. Normal session expiry, deletion and model-processing notices apply.

The production build and 98 backend tests passed. A
[browser check](../evaluation/blocked-video-browser-2026-11-04.json) uses a simulated
provider block and real local demo session/retrieval endpoints to verify recovery,
confirmation invalidation, provenance, grounded answers and deletion. This does
not demonstrate that hosted automatic YouTube imports have become reliable.
