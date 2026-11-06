# Family-scene speaker ownership

In the fictional family sample, the AI is the family member **requesting help**.
The learner is the person who declines and owns the boundary about their time.
Document practice instructions and example refusals address the learner; quoting
them does not make them appropriate partner dialogue.

The server now supplies an explicit role contract with localized positive and
negative examples for English, German and Spanish. Both generation and mandatory
evidence review receive it. A separate, narrow lexical guard rejects known
refusal/ownership reversals even when the model reviewer approves them. Rejected
dialogue is replaced with a localized clarification, without its source cards,
before the text can reach voice playback. This guard is limited to the known
family sample; custom relationships are not silently assigned that scenario.

The sample also has bounded practice pacing in demo and live mode: a first ordinary
refusal gets one localized, gentle follow-up; a repeated refusal or explicit
stop/no-further-requests boundary is accepted. These short server-owned replies
add no document facts or citations. Role/evidence validation still runs before a
live reply is delivered. Other questions can continue naturally. The helper uses
narrow multilingual patterns rather than a general semantic intent classifier;
`backend/test_family_pacing.py` verifies the bounded sequence in all three languages.

## Evidence-based progress for the standard family goals

The standard family sample now starts with three stable, editable action goals
rather than model-rephrased variants. A custom situation goal still uses live
mission generation. For unchanged standard goal texts, a bounded multilingual
recognizer can add missed progress using the latest learner message verbatim:
refuse help, state a request/time boundary, and maintain the refusal after the
server's actual gentle follow-up. Restatement needs that preceding delivered
follow-up; the first refusal alone cannot complete it. These communication actions
are `not_applicable` to document confirmation, never new confirmed source facts.
Previously achieved evidence is preserved. Custom edited goals retain live model
assessment; unknown paraphrases can still be missed by this narrow backstop.

For example, `Este fin de semana no puedo ayudar.` completes refusal. After the
gentle follow-up, `No me lo vuelvas a pedir. Pregúntame antes de contar con mi
tiempo.` completes the boundary and restatement goals. Tests force the model to
miss every action and check 1/3 → 3/3 in the turn response and final review, across
all conversation/feedback language combinations. Quoted examples, translation
requests, hypothetical statements, questions and keyword-only text do not earn
extra credit from the recognizer. This supplements the existing assessment; it
does not establish general scoring accuracy. Existing browser-saved reviews are
historical snapshots and are not automatically rescored.

`evaluation/family-role-regressions.json` contains 10 invalid and seven valid
partner replies per language. The cases include the reported German failures,
their English/Spanish equivalents, polite/formal requests and correct acceptance
of the learner's boundary. The API tests run each case in Everyday, B1 and B2:
153 cases in total. They deliberately make the reviewer approve every proposal,
including proposals with valid source IDs. Tests check the delivered dialogue,
withholding flag, source removal, learner text preservation and goal ownership.

The [recorded offline run](../evaluation/family-role-offline-2026-11-06.json)
passed 51/51 cases per language, with zero provider calls. CI runs the same matrix
and uploads its report with the evaluation artifacts.

Run the offline matrix and save actual results with:

```powershell
python scripts/evaluate_role_boundaries.py --output .runtime/role-boundaries.json
```

The runner uses no provider calls and exports source hashes, individual outcomes
and per-language totals. These are deterministic code regressions, not tests of
new model generations or proof that every paraphrase is covered. The lexical
guard can miss unseen wording or withhold legitimate replies. Broader model-level
reliability still requires repeated live multi-turn tests and independent review.

The existing `scripts/evaluate_family_roles.py` remains a separate paid live
check. On 6 November 2026 the daily reservation allowance was exhausted, and the
user explicitly chose to keep it unchanged and run offline tests only. No live
multilingual result is claimed for this update.
