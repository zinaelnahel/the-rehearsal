# Evaluation plan

## Multimodal implementation checks

[The implementation guide](docs/MULTIMODAL.md) documents the new offline contracts,
speech activation, cross-process Chroma test and explicit LangSmith experiment
runner. Run `python scripts/evaluate_langsmith.py` to upload fictional fixtures
and trace demo evaluation; add `--live --judge` for paid generation, agent tools
and the four model judges. This source integration is not itself a hosted result.
Historical provider reports below predate the new agent and speech paths.

Before claiming multimodal quality, record labelled EN/DE/ES audio/video fixtures,
word error rate and timestamp accuracy, microphone permission/silence/failure
flows, transcript corrections and playback of validated replies. Measure speech
latency and cost separately. Do not score pronunciation from STT text. Publish a
LangSmith experiment link and a reviewed live-agent run with source/configuration
hashes. Normal learner sessions and raw media are not uploaded to LangSmith.

## Missing-policy status regression

A production smoke review found that live role-play could correctly cite an
unspecified pet policy while incorrectly marking the answer confirmed. The live
proposal and evidence-review instructions now distinguish missing information
from a known answer. A conservative server-side lexical check prevents explicit
missing-detail source quotations from becoming confirmed even if both model calls
misclassify them. It checks the quoted sentence rather than unrelated missing
facts in a passage. It is not a general semantic classifier.

Deterministic regressions cover English, German and Spanish absence wording,
learner action completion independent of answer resolution, review follow-up
preservation, shortened source quotations and known prohibitions. All 55 backend
tests and nine offline RAG cases pass locally. This fix has not yet been validated
against a real provider or deployed; the historical reports below predate it.

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

## Navigation and download verification

The full deterministic command now passes 39 tests. New cases cover resuming a finished conversation without losing turns, invalidating the old review and rating, requiring explicit reset before replacing a scene, keeping state intact after invalid restarts, and preventing ordinary role-play from resuming a safety pause.

The local Chrome check verified clickable reached steps, source-draft edits that do not change the active scenario/language, plan edits isolated from current goals, preservation of unsent messages and review ratings during navigation, a successful UTF-8 conversation/review download, resume and a fresh review, cancelled/confirmed restarts, a failed mission rebuild preserving the prior scene, mobile overflow and session deletion. The exported file includes actual dialogue and review but excludes unsent text and unapplied goal edits. Downloads are user-initiated and created entirely in the browser; no export endpoint or additional server persistence exists.

A separate Chrome recovery check deleted a synthetic session on the server mid-scene. The frontend showed the timeout/restart explanation, downloaded only visible committed turns (excluding the unsent/failed reply), preserved typed source context on fresh start, and successfully created a new rehearsal.

## Family-boundary sample

The former shared-plans fixture is replaced by a fictional family member requesting help with weekend errands. Dedicated English/German/Spanish demo packs align the opening, goals, hint starters, vocabulary, partner pushback and review phrases. The sample requires neither an apology nor an alternative offer and invents no specific relative or prior family history. Custom difficult-conversation documents retain the general pack; an explicitly final breakup retains its separate pack even when the family sample was selected.

The full deterministic suite passes 44 tests, including the 36-combination language/scenario matrix and new checks for clear refusal, continued boundaries, in-character partner replies, personal actions marked not applicable to document answers, and isolation from custom/breakup contexts. Safety interruptions retain priority over the family script.

The final four-call fictional English live smoke check kept the partner in the family-requester role and recognised both the refusal and request to ask before assuming availability. See [the synthetic report](evaluation/family-boundary-smoke-2026-11-02.json). Earlier checks exposed role inversion and document-only fallback; explicit family roles and action guidance were added before the passing run. This small check is not a broad reliability measurement. Additional deterministic tests distinguish a short no from an inability to say no and allow exact two-letter refusal evidence while retaining independent semantic review.

Film wording uses the existing actions: **Action - start Take 01**, **Cut - finish & reflect**, and **That's a wrap** on ordinary review. Safety-paused scenes retain plain support wording. No sound, timer, new screen or extra click is introduced.

## Default apartment-turn validation fix

A user retest reported that an ordinary rent question still failed with an invalid answer-goal error. The previous successful smoke run was inadequate for this path because it replaced generated mission goals with hand-edited goals. In a pre-fix reproduction using fresh default three-goal apartment missions, the informal rent question failed the sibling mission-goal validator: the model emitted the goal's text as its ID. The same free-ID structure also allowed unknown or repeated answer-goal IDs. [Synthetic pre-fix record](evaluation/rent-before-fix-2026-11-02.json).

The provider now fills a closed object with exactly one required assessment slot per current mission goal. Goal IDs and separate answer-check arrays are absent from this generated format. The server binds slots to its own IDs, then uses the existing exact learner quote, retrieved source quote, citation and independent semantic/evidence validation. Replay slots bind to the original goal ID, not the slot number. User goal text stays untrusted data and never enters schema descriptions/keys. A bounded schema cache holds server-owned counts/source IDs only. The unchanged canonical internal format is retained for evidence review and adversarial tests.

The full deterministic suite passes **49 tests**. New regressions cover forbidden goal text/unknown slots/duplicate answer arrays, required assessments, retrieved-source enums, supported turn progress, nonzero replay IDs and atomic rejection of fabricated quotes. The provider-compatible schema contains no description siblings on `$ref` nodes. The application does not silently switch to demo, weaken quotation checks or automatically retry failed turns.

The stronger live check passed **eight fresh generated-mission takes**, covering three English rent phrasings repeated twice, German and Spanish, source-backed rent replies, source-confirmed goal tracking, availability follow-ups, review notes quoting the actual learner messages, replay and verified deletion: **40 provider calls**, no failed turns in the final run. [Synthetic fixed-slot report](evaluation/rent-fixed-slots-2026-11-02.json). The existing custom-goal/negation/translation/multilingual regression also passed: **27 calls**. [Multilingual report](evaluation/multilingual-fixed-slots-2026-11-02.json).

Repeat with `python scripts/evaluate_rent_flow.py`; this uses the configured provider with fictional material and writes only a local synthetic report. The original user session and transcript were not retrieved or retained. These small passing runs do not establish the broad reliability gates earlier in this document; production browser verification should also exercise default generated goals without editing them.
# Repeatable RAG benchmark

The local benchmark follows the evaluation dimensions in
[LangChain's RAG evaluation tutorial](https://docs.langchain.com/langsmith/evaluate-rag-tutorial).
It uses `evaluation/rag-dataset.json`: nine fictional apartment questions covering
rent, availability and an unspecified pet policy in English, German and Spanish.
Each case starts a fresh session, exercises the real retrieval and turn endpoints,
and verifies session deletion. Existing application source files are not modified.

```powershell
python scripts/evaluate_rag.py
python scripts/evaluate_rag.py --live
python scripts/evaluate_rag.py --live --judge
```

The default run forces demo mode even if `.env` enables live mode; it makes no
provider calls. Deterministic checks cover relevant evidence retrieval, expected
answer status, goal detection, citation integrity, exact quote support and required
answer values. These are narrow regression checks, not semantic correctness scores.

`--live` uses the configured provider for mission creation and the application's
two-call role-play/evidence review. `--judge` independently grades correctness
against the reference answer, answer relevance, groundedness against retrieved
passages and retrieval relevance. It adds four calls per case and can also grade
demo answers without `--live`. All calls use the configured model, timeouts and
application call limits. A nine-case live run normally takes 27 calls; adding the
judge brings that to 63. Provider calls may incur costs. Judge scores are estimates;
the same configured model is used, so correlated mistakes remain possible.

Reports default to `.runtime/rag-evaluation.json`; `--output` changes the path and
`--dataset` selects another dataset with the same fields. Reports include fictional
questions, answers, retrieved passages, individual checks and aggregate scores.
Errors count as failures; the process exits nonzero if any case fails. No LangSmith
dataset, experiment or trace is uploaded. Application tracing remains disabled.
Use only synthetic data in this runner, particularly when model grading is enabled.

The initial offline run passed all nine cases with zero provider calls. Live and
judge modes have not been validated against a provider as part of this addition.
This small apartment dataset does not establish quality across other scenarios,
long documents, adversarial instructions or multi-turn conversations. Extend the
dataset and review the expected evidence before comparing retrieval changes.
