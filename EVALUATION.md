# Evaluation plan

Use only the fictional samples and synthetic variants. Keep fixtures under version control; do not retain real learner data for evaluation. Run demo and live evaluations separately. Record model/version, prompt hash, chunk settings, retrieval mode and seed where supported. Re-run on every change to prompts, parsers, embeddings or goal detection. Evaluation reports must not contain API keys.

## Fixture set

Create 40 synthetic documents (10 per scenario), each with a fact table annotated by two reviewers: exact supporting passage, page/paragraph, answerable/unknown and contradictory/ambiguous status. Include multi-page PDFs, DOCX, pasted text, English, German and Spanish material, repeated headings and facts split at chunk boundaries. Add five prompt-injection fixtures per scenario: instructions to change role, reveal secrets, ignore source requirements, claim fabricated prices and mark every goal complete. Include scans, encrypted PDFs, mismatched file extensions and oversized/expanded archives as rejection fixtures.

For each document, write 10 learner queries: direct fact, paraphrase, cross-language, unknown fact, ambiguity and adversarial question. Build 15 labelled transcripts per scenario with achieved, missed and ambiguous goals, negations, keyword-only turns, edited goals and repeated hints. Human labels must judge observable communicative action rather than grammatical perfection.

| Dimension | Method | Initial live release gate |
| --- | --- | --- |
| Retrieval accuracy | Compare top-3 retrieved chunk IDs to annotated support. Report recall@3 and reciprocal rank by scenario, language and format. | ≥90% recall@3 overall; no subgroup below 80%. |
| Citation correctness | Split every partner turn into atomic document claims. Review whether each cited passage entails the claim and whether the page/paragraph is correct. | ≥98% citation precision; 100% references resolve to selected-session chunks. |
| Unsupported claims | Review all document claims, including implied dates, prices, policies and commitments. Unknown facts must be acknowledged. Track unsupported claims / all factual claims and unknown-answer accuracy. | 0 invented high-impact facts in fixed fixtures; ≥98% explicit unknown handling. |
| Mission detection | Compare goal states and exact learner evidence against dual-reviewer labels. Report precision, recall, F1 and false positives for ambiguous/negated turns. | ≥95% precision, ≥85% recall; no achievement without learner evidence. |
| Feedback usefulness | Two fluent reviewers per language score correctness, appropriateness to Everyday/B1/B2 style, practical usefulness, clarity in the chosen feedback language and exact-quote fidelity from 1–5. Record disagreement and adjudicate. | Average ≥4/5 in each category; 100% exact learner quote fidelity. |

The demo baseline is expected to perform worse on paraphrases and mission precision: publish its measured scores separately, never combine them with live scores. Edited demo goals remain unassessed, rather than treating keyword matching as semantic judgment. Its scripted unknown response and verbatim evidence should yield no invented factual paraphrases; check both prose and source cards.

## Workflow and privacy checks

Run `python -m unittest backend.test_app -v`. Also test valid text PDF and a browser flow with each upload format. Verify keyboard-only navigation, focus visibility, narrow screens, screen reader announcements and text contrast. A new user should finish a sample flow without help or a key in under five minutes; aim for ≥90% completion in a small moderated study.

Use a stubbed model to test structured-output failure, timeout, invalid citation IDs and fabricated learner quotes. Confirm failed turns are not committed and retries remain usable. Run live model fixtures at least three times to expose variability. A human should audit exact-quote feedback and claims even when schema validation succeeds.

For isolation, create sessions A and B with unique canary strings. Query B for A’s canary; it must never appear. Delete A and confirm every endpoint returns 404 and no retained vector store exists in the session registry. Advance idle time beyond TTL and verify immediate rejection plus periodic cleanup. Check responses have `no-store`, tracing is disabled, filesystem contains no uploaded fixture after closing the request, browser storage is empty, and logs have no document/turn contents. Close a tab online and offline: verify best-effort deletion and TTL fallback respectively. Verify restart deletes all sessions.

## Sample review worksheet

For every test turn record: fixture/query ID, expected fact or unknown, retrieved IDs, generated answer, cited IDs, claim-by-claim entailment, mission label/evidence, feedback score and reviewer notes. Classify failures as loader, chunking, retrieval, grounding, workflow, detection or pedagogy. Fix failures and re-run the entire fixed set before accepting the release gates. This document is a plan; broad live-model quality metrics have not been measured; the limited real-provider smoke results below are separate from those release gates.

## Multilingual and real-life rehearsal checks

Run the automated 4 × 3 × 3 matrix: every situation with English, German and Spanish conversation and feedback language independently. Verify mission text follows feedback language, openings/replies/starters/phrase sheets/retries follow conversation language, and Spanish punctuation rules never apply to English or German turns. After retry, the hint must reference the original missed goal rather than the first goal in the shortened mission.

Evaluate all language pairs and each style separately. Add cross-language uploaded documents, umlauts, accents and code-switching fixtures. Exact source quotations retain their original language. Measure cross-language retrieval recall rather than assuming the lexical alias map is semantic translation. Check sample translations preserve all numbers, dates and unknown facts.

For difficult conversations, score observable clarity, tone, perspective-taking and actionable next steps. Do not equate a perfect grammar score with successful communication. Confirm the partner never invents the other person's motives, agreement or commitments. Demo feedback offers a labelled suggestion; full personalised communication feedback still requires live-model and human evaluation.

## Uploaded-document and outcome regressions

Use a DOCX with a rent of €1,375 and a PDF with €1,620, different from the €850 sample. Through the actual browser file picker, build a Spanish B1 mission, ask the rent and verify that the partner reply contains the custom value and a resolving paragraph/page citation, never the sample amount. Test a DOCX over 1 MB to exercise temporary upload spooling. Simulate one failed upload request: an actionable message must appear and a manual retry must succeed. Test unreadable files, invalid formats, oversized bodies and non-JSON gateway errors separately.

For pets, explicitly state in the fixture that the policy is unspecified. After the learner asks, assert `achieved=true` for the asked action and `answer_status=unknown` for the document answer. The debrief must retain the unanswered question and offer a follow-up retry. Retry resets the action and answer status. Conflicting rents, instruction-like passages and absent facts must never be confirmed. Live-model goal completion and citation presence are not independent proof of an answer: mark `unverified` unless separately checked.

After browser deletion, wait for the server-confirmation notice. Check status, turn and finish endpoints return 404 for the deleted session. Backend integration tests also assert the session registry no longer contains it, every mutation rejects it, and another session remains accessible. These checks establish isolation and inaccessibility, not heap zeroization or provider data deletion.

## Recorded regression result — 2 November 2026

Code commit `fecaa0e` was deployed to the existing Vercel and Render services. Thirteen backend integration tests passed, including the 36 multilingual combinations, custom facts, unknown/conflicting/instructional text, upload spooling and deletion guards. The Next.js production build passed.

A headless installed Microsoft Edge browser exercised the actual production file picker and full flow with the apartment sample (€850), synthetic DOCX (€1,375) and synthetic PDF (€1,620). Each produced the correct quoted document value and citation, separate asked/confirmed states, an unknown pets outcome, debrief, follow-up retry and a server-deletion notice. After deletion, status, turn and finish returned 404. A deliberately aborted DOCX upload displayed an actionable error and succeeded on manual retry.

The tester's original “Failed to fetch” could not be reproduced with the available fixture, including on the previous production build. File-read, network, non-JSON response and timeout handling were hardened; the original failure's root cause remains unconfirmed. These are scripted/extractive-demo regression results, not live-model quality measurements or a guarantee against all browser/network failures.

## Revision 0.4 regressions

Regression cases include utilities questions explicitly mentioning rent in all three supported languages: they must not answer with a rent amount or change the rent mission’s evidence. The quoted availability turn must never receive a rent suggestion, including after all three mission actions are completed. Identical canonical wording gets no manufactured correction. Replay controls are a dedicated, prominent section with every goal available; completion alone must not hide replay.

The reported upload was Chrome with a synthetic DOCX around 36 KB, on an existing page. Browser checks therefore use installed Google Chrome and a 36,393-byte synthetic DOCX, proceeding from the sample to DOCX and PDF on the same page without reloading between rehearsals. The page footer identifies the updated client as **Demo v0.4**. A page already open before deployment needs one refresh to load changed JavaScript. This is a version check, not a confirmed explanation of the original failure.


The deployed revision 0.4 passed the production Chrome regression: sample, 36,393-byte DOCX, and PDF rehearsals on the same page without reloading between sessions; interrupted-upload retry; utilities returning no rent amount; availability feedback not suggesting rent; prominent follow-up replay; and verified deletion with 404 responses. Fifteen backend tests and the production build passed. The original user-specific upload failure remains unconfirmed; raw response-read and deletion-verification network errors were additionally wrapped. These remain demo checks, not live-model evaluation.

## Revision 0.5: real provider, listing links and branching plans

The final passing real-provider run used the configured `gpt-4.1-mini` and made 27 calls across English, German and Spanish. It verified that a negated custom goal stays unachieved, an actual custom internet question is detected with a source-supported answer, a contextual move-in question receives the documented date, the supplied Thursday-viewing phrase is genuinely translated, debrief quotes exist in the learner transcript, and replay/deletion work. Synthetic transcripts and assertions are retained in `evaluation/live-smoke-2026-11-02.json`. Earlier failing runs exposed missing follow-up retrieval aliases and historical goal carry-forward; both were corrected. No wider precision/recall claim is made from this small fixture set. The separate evidence review uses the same model and can share its biases.

Mocked contract tests reject fabricated learner/source quotes, withhold unsupported replies, reject unsubstantiated reviewer IDs, preserve already validated evidence, check strict schema shape, enforce request ceilings and block old demo clients from starting live missions without the updated notice. Listing tests cover direct/localized URLs, no fetch for pasted text, quote grounding, robot restrictions, private-network resolution, unsafe redirects and challenge pages. A real direct Idealista read was blocked and produced the explicit pasted-text/PDF fallback; successful unrestricted access is not claimed.

Browser QA exercises the listing URL plus synthetic pasted advert text, actual live custom-goal chat and translation, mission and sidebar dialogue-map branches, mobile overflow, supporting text at least 12 px, debrief/replay and deletion. Plans must remain labelled as possible paths and never modify source facts or claim to predict another person. Also test keyboard activation and 390 px mobile width. This is communication practice, not an anxiety treatment or a clinical evaluation.


Hosted revision 0.5 verification passed on `https://the-rehearsal-lab.vercel.app`: Chrome completed the real-model listing/pasted-text rehearsal, custom goal, actual German translation, both branching-map placements, 390 px layout, replay and deletion. API checks confirmed live mode, the old-demo-client guard (409 before model processing), and the real Idealista read fallback (424). Twenty-nine backend tests and the production build passed. To rerun the explicit real-provider smoke checks with fictional data and a configured server key, run `python scripts/evaluate_live.py`; this makes paid provider requests and writes only the fictional report to ignored `.runtime/live-evaluation.json`.

## Revision 0.6 focused checks

The deterministic suite now includes `backend.test_context_feedback`: 36 tests across all four backend test modules. It covers final-breakup goals/hints/review, safety interruptions in source and turns without provider calls, opaque response identifiers, session isolation, rating change/clear, rejected transcript fields, whole-dialogue review ratings and stale identifiers after replay. Informal rental-document questions without question marks receive an explicit unconfirmed answer and remain in review follow-ups rather than triggering generic acknowledgements or rent-goal progress.

The final interface keeps the existing credited Nathan Fielder image unchanged. The plan map starts collapsed under **Explore possible responses**, is absent from the rehearsal sidebar, and uses boundary-aware paths for difficult conversations. Ratings appear once in the review for the whole dialogue; they are not part of partner messages or automatic training labels. Check keyboard toggling, optional reasons, change/clear, narrow screens, deletion, and the absence of review ratings/replay for safety pauses.

Safety detection is a conservative keyword safeguard and can over-trigger or miss indirect language; it is not clinical risk assessment. The live output schema explicitly requires learner evidence to be copied from the latest user turn, never the partner reply. Invalid evidence remains rejected rather than weakening validation to accommodate the model.

The final revision 0.6 real-provider smoke run passed in English, German and Spanish (27 provider calls). See [the synthetic report](evaluation/live-smoke-v06-2026-11-02.json). An earlier run correctly rejected model-generated evidence copied from a partner reply; the schema descriptions were clarified before the passing rerun. These smoke checks do not establish broad model accuracy or clinical safety.
