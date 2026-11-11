# Rehearsal sources

The three-entry sample picker offers the Madrid listing PDF, the Spanish
interview video and a fictional Spanish family-boundary audio conversation. The pinned originals in `documents/` and their provenance
in `catalog.json`. Conversation and feedback language do not replace or translate
the underlying source. The older apartment/interview/course text files remain
development fixtures; the application no longer serves them as samples.

- **Apartment:** `listingSpanish.pdf`, supplied by the user on 11 November 2026.
  Image-based Idealista / Darya Living listing. The original URL and capture date
  are unavailable. `listingSpanish.pages.json` contains a manual transcription
  checked against all three page images, bound to the PDF's SHA-256. Page order,
  the €2,400 monthly rent, €80 utilities limit and contradictory 31/80 m² figures
  are preserved. Navigation and promotional controls are omitted. The PDF is
  available for direct inspection; this is not a reconstructed PDF.
- **Video:** Habla con Eñe, *Cómo hacer una entrevista de trabajo en
  español*, level B2, selected explicitly by the user. The video URL is
  `https://www.youtube.com/watch?v=43tNZcBkcOE`. The interview sample defaults
  to Spanish and B2. YouTube captions are disabled. `interview-transcript.es.json` contains a
  prepared Whisper transcription of the actual 189-second video audio, obtained
  on 11 November 2026. The audio hash records the source used; downloaded audio
  is not shipped. AI transcription and segment timing are approximate and require
  learner review. Unchanged text retains source video timestamps; edited text
  uses text sections. The bundled sample makes no caption-import requests. The candidate's biography is not the
  learner's.
- **Boundary-setting voice message:** `audio/family-boundary.es.wav`, a short
  fictional Spanish voice message from a family member who has already counted
  on the learner for a Saturday move, ten until one, without asking first. It
  mentions moving boxes to the car and having already told others. The authored
  script is in `audio/family-boundary.es.json`; one AI-generated voice (cedar)
  reads the three segments. There is no prewritten learner response or outcome.
  Each segment's start/end is measured from its actual generated PCM bytes,
  including the inserted pauses. The metadata is bound to the WAV by SHA-256
  and validated against its duration. An unchanged reviewed transcript uses
  these timestamps; edited words fall back to text-section citations. The source
  viewer plays the selected excerpt and stops at its end. Specific recorded facts
  may be cited; acknowledgements, refusals and learner-provided availability
  do not receive decorative citations. Playback uses the bundled WAV without
  provider calls. To explicitly regenerate it (paid TTS), run
  `python scripts/generate_boundary_audio.py` with a configured provider key.


Saved source dates, prices and availability belong to the original material.
They do not imply a current vacancy, available apartment or open enrolment.
Publisher attribution and original links stay visible in the picker; citations
open the original document's page text and provide a link to the saved PDF.

Refresh connection-state previews with `python scripts/generate_sample_previews.py`.
Run source regressions with `python -m unittest backend.test_sample_sources`.

Uploaded recordings use the same source viewer. The original file remains in
browser memory for playback; the server removes temporary processing files.
A two-hour signed transcription receipt binds unchanged words and timestamps.
Edited transcripts (or expired receipts) use text evidence and full playback,
without excerpt timestamps. Restarting the server invalidates receipts, so
re-import before confirming a pending recording after a restart.
