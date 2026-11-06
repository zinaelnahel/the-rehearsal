# Revisit language practice on this device

The review offers **Remember this rehearsal**. Give the take a title, explicitly
agree to save the conversation/review, then select **Save rehearsal on this device**.
Nothing is saved automatically. **My saved rehearsals** is available on every
step, including while the backend is unavailable. Select a saved take to reread
its conversation, communication feedback, goals, open questions and useful phrases.
Filter by title, language or scenario, and optionally compare two takes side by
side. Goal counts are historical practice outcomes, not a measured language level.

The archive uses IndexedDB in the current browser profile and origin. This is
separate from a live server session: ending/deleting that session does not delete
an explicitly saved browser copy. The review and setup privacy text explain this.
The library has individual deletion (with confirmation), **Delete all saved
rehearsals**, and the existing explicit text download for backup. Saved conversations
cannot resume expired live sessions. Loading the app shell still requires the
frontend; this is not a fully offline/PWA implementation.

## Data and limits

Only an allowlisted snapshot is written: a client-generated archive ID, title,
save dates, scenario/language/style/mode/take, conversation turns, communication
notes, goal text/status, unresolved questions and phrase sheet. No server bearer
IDs, response IDs, feedback IDs, source-card payloads, original filename/file
metadata, source URL metadata, or audio blobs are copied. Conversation text and feedback can still contain
quoted facts or personal information from the rehearsal; this is disclosed as
saving the conversation, not an anonymized record. Support/paused scenes are not
offered for saving. Saving/reopening the same take updates one entry within that
page session; no cross-device or cross-browser identity tracking is introduced.

The store is versioned. Invalid entries are not rendered or silently discarded;
the user is told they can clear the library. There is a 100-entry / 8 MiB application
ceiling, a 1 MiB per-entry ceiling and bounded text fields. Limits fail without
truncating conversations or evicting older entries. Database changes are atomic;
the UI acknowledges success only after transaction completion. Closed/blocked or
quota-limited storage yields an error and leaves text download available.

This is convenience storage, not secure or backed-up storage. Anyone using the
same browser profile may read it. Private browsing, device cleanup, storage
eviction or clearing site data can remove records. No persistent-storage permission
is requested and no storage-survival guarantee is made. Localhost, preview URLs
and the public production URL have separate archives. Browser backup/sync policies
are outside the app's control. Nothing from the archive is sent for analytics,
shared feedback or AI inference when it is saved or read.

## Verification

`npm run test:library` checks snapshot privacy, validation/limits and unavailable
storage. The optional `scripts/test_library_browser.mjs` uses Playwright and real
IndexedDB with mocked backend responses to verify explicit saving, duplicate
updates, privacy exclusion, persistence after server deletion/page reload,
backend-unavailable reading, comparison, translation, mobile layout and deletion.
It makes no provider calls. Run it against a locally built frontend using
`LIBRARY_TEST_URL`; `PLAYWRIGHT_MODULE` and `CHROME_PATH` work like the other browser
verification scripts.
