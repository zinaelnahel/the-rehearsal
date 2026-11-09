# Engineering review — 9 November 2026

This review compares the current source with the relevant lessons in
[ai_eng_lesson_templates](https://github.com/zinaelnahel/ai_eng_lesson_templates/tree/main/K_LLM_APIs)
and checks reproducibility, security and release evidence. Teaching examples
are guidance, not a complete production certification.

| Practice | Implementation | Remaining limit |
| --- | --- | --- |
| Trusted instructions separate from input | System messages; JSON-encoded source, preferences and dialogue as data | Prompt injection remains an open risk, not a solved property |
| Structured outputs | Strict schemas, Pydantic validation, exact quotes and independent evidence review | Valid format does not establish factual correctness |
| Bounded tool execution | Read-only tool allowlist, validated arguments, time and call limits | Adds latency; usefulness needs broader evaluation |
| Conversation context | Verbatim recent-message windows, complete pairs when trimming, separate current evidence | Old context can fall out of the window; no semantic summary is claimed |
| Usage measurement | Provider token counts and call durations collected by callbacks, including failed output validation | Session-local numeric aggregates only; missing reports stay missing, and tokens are not dollar costs |
| Reproducible builds | Hashed transitive Python lock, npm lock, hash-checked installs in CI/Docker; CI checks input fingerprint | OS image/system packages are not bit-for-bit pinned |
| Dependency maintenance | Updated LangChain/LangSmith/OpenAI SDK, weekly audit and Dependabot, SHA-pinned Actions | Four unresolved Chroma server advisories have explicit expiring applicability exceptions; see SECURITY.md |
| Evaluation integrity | Shared manifest includes all backend Python modules and dependency lock; human reviews bound to output and source | Independent human-reviewed live benchmark remains missing |
| Privacy | No ordinary user-session tracing; metrics contain counts/durations only | Provider retention and server ephemeral-storage limits still apply |

## Reproduce

Local verification in a fresh environment installed from the hashed lockfile:
149 backend tests and 20 voice/library tests passed; all nine RAG regression
cases passed; 126/126 synthetic quality cases completed; 153/153 deterministic
role-ownership cases passed; translation coverage and the production frontend
build passed. All 18 sensitive-context cases continued without an application
pause. These are offline results, not live-model quality scores. npm reported
zero advisories; the Python check reported only the four documented Chroma
exceptions. No paid provider calls were made.

Use Python 3.12 and Node 22 for the same major runtime versions as CI:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python scripts/lock_dependencies.py --check
python -m pip install --require-hashes -r backend/requirements.lock
python -m unittest discover -s backend -t . -p 'test_*.py' -v
python scripts/evaluate_rag.py
python scripts/evaluate_quality.py --dataset evaluation/quality-release-dataset.json
python scripts/evaluate_role_boundaries.py
npm ci
npm run check:locales
npm run test:voice
npm run test:library
npm run build
```

Offline test runs need the CI request/budget limits rather than public deployment
limits; see `.github/workflows/ci.yml`. These checks use synthetic fixtures and
do not establish current live-model quality. SDK integration tests use simulated
HTTP responses, not paid provider calls.

To update Python dependencies, edit `backend/requirements.txt`, install `uv`,
run `python scripts/lock_dependencies.py`, review the exact versions and hashes,
and rerun CI. Do not install the range file into production. Run the security
workflow to audit the lockfile; scanner failures never count as clean results.

Model usage is attached to completed synthetic quality results as `model_usage`, with
request/failure counts, elapsed milliseconds, provider-reported input/output
tokens, and report coverage. It is not added to public product flows or shared
feedback. Normal session deletion/expiry removes those in-memory counters.

## Open improvements

1. Compare multilingual semantic embeddings against the lexical baseline using
   retrieval recall, latency, memory and cost. Do not silently send documents to
   an embedding provider before consent or load an unmeasured large model into
   the existing free host. No semantic retrieval improvement is claimed here.
2. Obtain independent, fluent human reviews of the live benchmark in all three
   languages. Keep missing verdicts and stale evidence as release failures.
3. Use that evidence consistently for releases. Previous manual deployments were
   user-requested exceptions, not evidence that the benchmark gate passed.
4. Revisit the Chroma advisories by 9 December 2026, or sooner if persistence or
   network exposure changes. Hosted durable storage remains unconfigured.

Deployment history remains in `DEPLOYMENT.md`; updating source and passing CI
does not by itself update the public application.
