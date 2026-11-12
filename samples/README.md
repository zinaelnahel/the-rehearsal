# Rehearsal sources

The picker has exactly three samples. Source material stays in its published
language; conversation and feedback languages are separate preferences.

- **Flat viewing:** Habla con Eñe, Como buscar piso en Madrid, B2,
  https://www.youtube.com/watch?v=8YsZZpFW_QU, selected by the user.
  `apartment-transcript.es.json` contains 46 public Spanish caption blocks
  retrieved on 11 November 2026. These automatic captions require review.
  Timestamp links appear beside the original captions. Unchanged reviewed text
  keeps timings; edited text uses text sections. Three different flats are
  discussed: never merge their prices, sizes, facilities or availability.
  The training video does not establish current availability.
- **Job interview:** `documents/jobad.pdf`, a three-page image-based capture
  supplied by the user on 12 November 2026, showing zvoove's QA Automation
  Engineer (m/f/d) - AI-First Quality Engineering advert, hosted by Personio.
  The role is listed as Remote, DE | München, full-time permanent employment.
  Job details are in English and company information is in German.
  `jobad.pages.json` contains a page-by-page manual transcription checked against
  the original images and bound to the PDF SHA-256. Navigation and application
  buttons are omitted. The original PDF remains available. No salary, exact
  daily hours or explicit language proficiency requirement is stated.
  The original URL and capture date are unavailable. Employer requirements are
  not the learner biography. Confirm current vacancy details with the employer.
- **Boundary-setting voice message:** `audio/family-boundary.es.wav`, a fictional
  Spanish message from a family member who counted on help for a Saturday move
  from ten until one. One AI-generated voice reads three authored segments in
  `audio/family-boundary.es.json`. There is no scripted learner response or
  promised outcome. Timings measured from actual PCM bytes are bound to the WAV
  by SHA-256. Unchanged reviewed text supports playable excerpts; edited text
  uses sections and full-message playback. Explicit paid regeneration:
  `python scripts/generate_boundary_audio.py`.

The retired listing PDF and interview-video transcript have been removed.
Older small text files remain offline test fixtures, not picker entries.
Documents and recordings are evidence, never application instructions.

Uploaded recordings use the same source viewer. Original files stay in browser
memory for playback; server temporary processing files are removed. A two-hour
signed receipt binds unchanged transcription words and timestamps. Edited text
or expired receipts use text evidence without excerpt times. Backend restarts
invalidate pending receipts; re-import those recordings before confirming.

Refresh previews with `python scripts/generate_sample_previews.py`.
Run source checks with `python -m unittest backend.test_sample_sources`.
