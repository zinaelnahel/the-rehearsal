# Conversation quality evaluation

`scripts/evaluate_dialogue.py` replays fixed conversation histories through the
production `/turn` endpoint. Retrieval, reply generation and the app's evidence
review remain real in live mode. Mission generation and the opening are fixture
inputs, keeping the latest learner turn and its context identical across runs.
It tests a next turn with multi-turn context, not a free-running conversation.
No public learner session is accessed. Test sessions are deleted even on failure.

The nine fictional English/German/Spanish cases include willingness to learn,
repeated questions, grammatical agreement, self-reported experience, corrected
dates, learner-requested topic changes, unknown training terms and unwanted
coaching. The reported Spanish interview inspired one synthetic regression.
Author labels are examples for reviewers, not human gold or automatic scores.

Six independent dimensions are graded: relevance, memory, continuity, role
consistency, grounding and language/agreement. Each grade is `pass`, `fail` or
`uncertain`, with a rationale and optional exact candidate quote. Missing and
uncertain judgments are never passes. This does not measure voice pronunciation.

## Run

Offline smoke run (zero provider calls; uses illustrative fixture replies):

```powershell
python scripts/evaluate_dialogue.py --output .runtime/dialogue-offline.json
python -m unittest backend.test_dialogue_eval -v
```

Live generation and separate model judging (paid; uses the configured provider
key and existing app budget controls):

```powershell
python scripts/evaluate_dialogue.py --live --judge-model gpt-4.1-mini --repeats 2 --output .runtime/dialogue-candidate.json
```

Each replay normally makes two app model calls plus one judge call. Nine cases
with two repeats normally use 54 calls. `--limit 1` bounds an initial smoke run
to one case. Provider failures and invalid judge outputs are recorded, and make
the runner exit nonzero. Semantic failures remain visible in the report metrics;
a successful process exit means execution completed, not that quality passed.
Tracing and optional agent planning are disabled for this isolated benchmark.

To check the evaluator against fixed positive/negative controls instead of
generating new replies, use `--live --judge-model gpt-4.1-mini --judge-fixtures`.
This makes one judge call per case; `--limit 1` tests the original hours-jump
negative control. Author defect labels remain hidden from the judge. These
control runs are marked `judge-fixtures` and cannot be compared as generated
application outputs or counted as human calibration.
They record missed author-labeled defects and positive-control failures and exit
nonzero when those controls are not satisfied. This prevents an all-pass judge
from appearing to validate its own usefulness.

Initial integration checks on 9 November 2026 completed one generated Spanish
replay plus separate judging. However, both `gpt-4.1-mini` and `gpt-4.1` falsely
passed the fixed hours-jump negative control, including with the revised rubric.
Do not rely on these initial judge configurations for automatic quality approval.
The control was used while developing the rubric, so it is a development case,
not held-out evidence. Independent human calibration remains unperformed.

The judge is a separate call, never the application's own evidence verdict. It
receives the history, latest message, candidate, full source, retrieved passages
and rubric. It sees no prompt revision, reference answer, author defect labels,
or app reviewer decision. Using the same model family can still share biases;
configure another evaluator model if available and calibrate with humans.

## Human review and calibration

Each report includes complete fixtures and outputs and writes a `.review.json`
worksheet beside it. Review the candidate in context before looking at model
ratings. Fill `reviewer` with an attributable reviewer identifier and `ratings`
with all six dimensions, using this shape for each dimension:

```json
{"verdict": "fail", "reason": "The learner expressed willingness to learn, but the partner jumped to hours.", "candidate_quote": ""}
```

Use `uncertain` when unable to decide. Do not fill human reviews with model
outputs. Leave `ratings` null for unreviewed cases. Preserve `run_id`, `report_id`
and `output_sha256`; stale, duplicate, unknown and unattributed reviews are rejected.
Then rescore without provider calls:

```powershell
python scripts/evaluate_dialogue.py --score-report .runtime/dialogue-candidate.json --reviews .runtime/dialogue-candidate.review.json --output .runtime/dialogue-reviewed.json
```

Reports keep model and human results separate and show paired dimension-rating
agreement and model false passes against human failures. These are descriptive
calibration results on reviewed cases, not proof of judge reliability. No human
coverage means no calibration claim.

## Compare prompt versions

Run the baseline checkout and candidate checkout with identical fixtures,
repeats, model configuration and judge. Preserve reports outside any files that
will be overwritten. Single-candidate judges never see a version label or the
other candidate. This reduces version bias, but is not a randomized pairwise
preference study. Human reviewers should likewise review anonymized candidates
without seeing version/model scores first.

```powershell
python scripts/evaluate_dialogue.py --live --judge-model gpt-4.1-mini --repeats 2 --compare-report .runtime/dialogue-baseline.json --output .runtime/dialogue-candidate.json
```

Comparison requires identical dataset/rubric hashes, judge configuration, case
IDs and repeat coverage. It counts paired improvements, regressions and unscored
cases per dimension, separately for model and human verdicts. Changed generation
models are allowed but are a comparison of configurations, not a prompt-only
experiment. Keep the generation model fixed for prompt-only comparisons.

This supplements the existing factual benchmark and release gate; it does not
automatically authorize deployment, convert model verdicts into human reviews,
or claim a passing production benchmark. Expand the small synthetic dataset
with reviewed failures and held-out cases before setting a release threshold.
