# Dependency and application security

Re-audited on 12 November 2026: npm reported zero vulnerabilities; the locked Python audit reported zero unexcepted findings and the four Chroma exceptions below. The upstream recheck confirmed 1.5.9 remains current and did not extend the exception expiry. See the [final audit](EVALUATION.md#final-project-audit-12-november-2026) and [engineering status](docs/BEST_PRACTICES.md).

Python runtime dependencies, including transitive dependencies, are pinned with
distribution hashes in `backend/requirements.lock`. CI and Docker install that
file with `--require-hashes`. `backend/requirements.txt` declares supported
version ranges; it is the input to the resolver, not the deployment lockfile.

The security workflow checks Python and npm dependencies on pushes, pull
requests, weekly, and on manual dispatch. Release also requires a successful
security run for the selected commit. Dependabot proposes dependency updates;
Python updates must regenerate the lockfile and pass CI before merging.

## Unresolved Chroma advisories

The [9 November review](evaluation/chroma-security-review-2026-11-09.json)
checked the latest PyPI release, all four upstream GitHub advisory records and a
fresh dependency audit. Version 1.5.9 remained latest and no patched version was
identified. The exception was reviewed, **not renewed**; its expiry stays unchanged.
Run `python scripts/review_chroma_security.py --audit-report .runtime/dependency-audit.json`
after a fresh dependency audit to repeat the online review.

The audit still reports four unique upstream Chroma advisories (some feeds
duplicate a finding). No patched version was available in the audit:

- [CVE-2026-45829](https://github.com/advisories/GHSA-f4j7-r4q5-qw2c): HTTP server collection creation and remote-code embedding configuration.
- [CVE-2026-45833](https://github.com/advisories/GHSA-36p7-vc44-83pf): HTTP server collection updates and remote-code embedding configuration.
- [CVE-2026-45830](https://github.com/advisories/GHSA-2wm9-hf6c-p5cr): HTTP server cross-tenant authorization.
- [CVE-2026-45831](https://github.com/advisories/GHSA-xph7-9rjv-w5fr): HTTP server RBAC scope enforcement.

Our applicability assessment is that those HTTP-server paths are not exposed:
the application does not start or proxy a Chroma server, and the public deployment
uses memory retrieval. Optional persistence uses only embedded `PersistentClient`,
server-owned collection names and `embedding_function=None`. It does not accept
remote model repositories or embedding-function configuration from visitors.
This is an architecture-based assessment, not proof that the package is free
of vulnerabilities.

The adapter is now explicitly fixed to `chromadb.api.rust.RustBindingsAPI` so
environment configuration cannot select the HTTP client. Regression tests cover
that invariant, server-owned hashed names and source text remaining document
content rather than embedding-function configuration. The audit runner requires
a new report for each invocation: a scanner failure cannot reuse an older clean
report. These tests support the assessment; they are not an independent exploit
or penetration-test result.

These exact advisories on `chromadb==1.5.9` have a visible, version-scoped
exception in `security/dependency-exceptions.json`, expiring **9 December 2026**.
The check prints every exception and fails for any new finding, skipped package,
changed affected version or expired exception. Reassess before changing storage
architecture; this exception does not cover running a Chroma HTTP service.

## Data and trust boundaries

Provider keys stay on the server. Tools are read-only, session-bound and bounded
by argument schemas, timeouts and call limits. Uploaded content is untrusted;
strict output schemas are followed by separate quote and factual-support checks.
Document parsers run in confined processes on supported production hosts.

Normal user conversations are not uploaded to tracing services. Model metrics
retain only counts and durations in the expiring session: no prompt/reply text,
provider request IDs or credentials. Sharing feedback remains opt-in. Numeric
token counts are provider-reported usage, not a billing estimate or replacement
for account-level spending limits.

The application no longer performs danger-keyword scanning or forced support-note
pauses. This does not remove input validation, source-grounding checks or tool
permissions. Model-provider behavior is independent of these application rules.
