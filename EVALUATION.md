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

For every test turn record: fixture/query ID, expected fact or unknown, retrieved IDs, generated answer, cited IDs, claim-by-claim entailment, mission label/evidence, feedback score and reviewer notes. Classify failures as loader, chunking, retrieval, grounding, workflow, detection or pedagogy. Fix failures and re-run the entire fixed set before accepting the release gates. This document is a plan; no live-model quality metrics have been measured yet.

## Multilingual and real-life rehearsal checks

Run the automated 4 × 3 × 3 matrix: every situation with English, German and Spanish conversation and feedback language independently. Verify mission text follows feedback language, openings/replies/starters/phrase sheets/retries follow conversation language, and Spanish punctuation rules never apply to English or German turns. After retry, the hint must reference the original missed goal rather than the first goal in the shortened mission.

Evaluate all language pairs and each style separately. Add cross-language uploaded documents, umlauts, accents and code-switching fixtures. Exact source quotations retain their original language. Measure cross-language retrieval recall rather than assuming the lexical alias map is semantic translation. Check sample translations preserve all numbers, dates and unknown facts.

For difficult conversations, score observable clarity, tone, perspective-taking and actionable next steps. Do not equate a perfect grammar score with successful communication. Confirm the partner never invents the other person's motives, agreement or commitments. Demo feedback offers a labelled suggestion; full personalised communication feedback still requires live-model and human evaluation.
