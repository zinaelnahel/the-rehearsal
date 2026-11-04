# Quality benchmark — 4 November 2026

This is a measured baseline, including failures, not a claim of production
readiness. The 36 fixtures have author-authored synthetic labels, not independent
human labels. They cover three languages, twelve categories and three scenarios.
Each case was run once. The agent preparation step was disabled to isolate
generation and mandatory independent evidence review; retrieval used memory.
These results do not benchmark the full hosted agent flow or persistent Chroma.

| Reference-based measure | Live | Scripted demo |
| --- | --- | --- |
| Cases completed | 36/36 | 36/36 |
| Goal precision | 30/33 (90.9%) | 21/27 (77.8%) |
| Goal recall | 30/30 (100%) | 21/30 (70%) |
| Goal F1 | 95.2% | 73.7% |
| Answer-status accuracy | 30/36 (83.3%) | 18/36 (50%) |
| Answerable cases confirmed | 24/24 | 12/24 |
| Answerable cases withheld | 0/24 | 0/24 |
| Unknown/ambiguous cases wrongly confirmed | 3/6 | 0/6 |
| Supporting evidence retrieved in top four | 36/36 | 36/36 |
| Citation references resolve to retrieved text | 36/36 | 36/36 |

Demo's zero false confirmations is not evidence that demo is better overall:
its goal recall and confirmation coverage are much lower. Exact supporting text
and a valid citation do not establish correct interpretation or entailment.

## Failures the benchmark exposed

- All three keyword-only learner turns were marked as achieved in live mode,
  contrary to the authored goal labels. The reference-label goal precision
  therefore falls below the proposed 95% evaluation-plan target.
- All three conflicting-price fixtures were marked `confirmed` instead of
  `unknown`. In English and Spanish, the answer prose acknowledged both prices,
  but the confirmation state was still wrong. In German the answer asserted
  one conflicting price; the API judge flagged that answer as unsupported.
- The exact-value proxy matched 18/21 live answers; numeric formatting alone can
  fail that lexical check, so it is not a semantic accuracy measure.

The initial API judge used `gpt-4.1-mini`, the same model family/configuration as
generation, in a separate call. It flagged unsupported prose in **1/36** answers
and marked **33/36** answers correct. These are model opinions, not a measured
human-ground-truth hallucination rate. It incorrectly treated several
keyword-only turns as valid requests and criticized valid responses to negated
requests for not fulfilling the negated goal. Its `goal_correct` field is not a
reliable substitute for the reference-label confusion matrix. A judge needs
calibration as well as the application.

## Evidence and reproducibility

- [Fixtures](quality-dataset.json)
- [Live answers, reference checks and API verdicts](quality-live-judged-2026-11-04.json)
- [Offline demo baseline](quality-demo-2026-11-04.json)
- [Unfilled live human-review worksheet](quality-live-judged-2026-11-04.review.json)

The live run made **144 provider calls**. Reports include source/dataset hashes,
full fictional source documents, answers, evidence, category/language breakdowns,
and descriptive Wilson intervals. There are **zero human-reviewed answers**.
The observations are correlated across translated fixtures; the intervals do
not establish generalization. Repeats, long-document tests, multi-turn tests,
human adjudication and a complete agent-enabled run remain outstanding.

The optional local judge in `scripts/judge_quality_ollama.py` scores these saved
answers without regenerating the conversation or making OpenAI calls. It keeps
the original API verdicts, validates local structured output, records local model
identity and compares paired verdicts. A different model's agreement is not proof
of accuracy. Human review should focus on failures and judge disagreements.

## Ollama comparison: completed, with poor judge consistency

The installed local `qwen3:4b` model (Q4_K_M, digest recorded in the report)
attempted all 36 saved live answers. It returned 32 valid verdicts, of which
seven said `uncertain`; four requests produced incomplete output. Therefore
only **25/36** answers had an evaluable local grounding verdict. No extra OpenAI
calls were made and the original answers/API verdicts were preserved.

Across those 25 paired evaluable answers, exact grounding-category agreement
was **1/25 (4%)**, answer-correctness agreement **3/25 (12%)**, and goal-verdict
agreement **16/25 (64%)**. The local judge labeled 23/25 answers unsupported.
**That is not a measured 92% application hallucination rate.** Its explanations
include incorrect objections to citation markers and ordinary conversational
follow-ups, confusion between learner and partner actions, and altered numeric
quotations. The source-only judge payload does not explicitly map citation IDs,
which is a limitation of this judge setup, especially for the smaller model.
The API judge also made goal-assessment errors, as described above.

This local model/rubric configuration is **not validated as a replacement judge**.
Do not choose the judge that gives the more favorable score. Next steps are a
human-labeled calibration set, clearer separation of goal-detection correctness
from goal fulfillment, citation metadata for grading, and explicit allowance for
non-factual conversational questions. Any revised rubric must be tested on a
held-out set rather than silently replacing these baseline results.

See the [full local verdicts, failures and comparisons](quality-ollama-2026-11-04.json).
All 91 backend tests passed after adding the local-runner validation tests; those
tests verify code behavior, not the model's judgment quality. No application
behavior was changed or deployed by this evaluation work. Baseline generation
used source commit `7b2417e6e70d26b2158c009f74f1e87cfeb91bf0`.

## Rent-conflict fix: separate post-fix run

The [new server guard](../docs/RENT_CONFLICTS.md) was tested on the same 36
unchanged fixtures. The original live/API/local-judge reports above are preserved.
See the [post-fix live report](quality-live-postfix-2026-11-04.json) for complete
answers, source hashes and reference checks.

| Reference-based measure | Before | After |
| --- | --- | --- |
| Completed | 36/36 | 36/36 |
| Answer-status accuracy | 30/36 (83.3%) | 33/36 (91.7%) |
| Conflicting-price false confirmations | 3/3 | 0/3 |
| Unknown/ambiguous false confirmations (all six cases) | 3/6 | 0/6 |
| Answerable cases confirmed | 24/24 | 24/24 |
| Answerable cases withheld | 0/24 | 0/24 |
| Goal precision / recall | 90.9% / 100% | 90.9% / 100% |

All three conflict responses were replaced with localized clarification text,
kept their conflicting source cards and recorded the factual answer as unknown.
The remaining status failures are the same three keyword-only goal detections.
This final run made 108 provider calls, with agent preparation and the extra
evaluation judge disabled. It still exercised the application's mandatory
generation and evidence-review calls. A preceding 12-case targeted smoke check
also passed, using 36 calls; the full report is the published post-fix comparison.
All 96 deterministic backend tests passed.

This is a single-run synthetic regression result, not a general hallucination
rate or human calibration. The guard's lexical/retrieval limits and possible
conservative withholding of legitimate alternatives are documented separately.
The post-fix report describes local real-provider verification, not a hosted
deployment check. Human review and agent-enabled regression remain pending.
