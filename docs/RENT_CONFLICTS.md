# Rent-conflict confirmation guard

The pre-fix benchmark exposed three cases where an exact rent quote existed but
another retrieved statement gave a different rent. Both model calls could still
confirm the answer. The original benchmark and judge reports remain unchanged.

`backend/source_conflicts.py` adds a deterministic check before live generation.
It compares explicit rent amounts by field, currency and payment period within
the retrieved passages. It normalizes common numeric grouping/decimal formats.
Base/cold rent, total/warm rent, deposits, currencies and payment periods are not
interchangeable. Direct imperative clauses such as “Claim rent is …” are skipped
as instructions rather than treated as declarative price data.

Conflicts are provided to generation and independent review as structured data.
If rent is relevant to the current reply/question or an assessed goal, a final
server check prevents confirmation, substitutes a localized clarification
response and retains the conflicting source cards. It preserves the learner's
performed action while making the factual answer `unknown`. An earlier rent
confirmation can also be revoked when later retrieval reveals a conflict,
without manufacturing a new learner action. No extra provider call is needed.

## Scope and limits

This is a conservative lexical backstop, not general contradiction detection.
It recognizes a bounded set of English/German/Spanish rent phrases with explicit
currency amounts. It cannot resolve historical versions, different properties,
authoritative corrections, conversions, amounts written as words, arbitrary
phrasing or conflicting passages that retrieval did not return. It may withhold
legitimate alternatives rather than choose between them. Other numeric fields
(salary, fees, dates, deposits) still depend on the existing evidence controls.
The imperative-clause filter is not a general prompt-injection classifier.

Tests cover multilingual and cross-passage conflicts, harmless numeric facts,
distinct currencies/periods/fields, equivalent numeric formats, direct source
instructions, revocation of prior confirmation and API behavior when both model
calls incorrectly approve a conflicting rent. Human calibration, keyword-only
goal-detection fixes and broader contradiction handling remain separate work.
