# Lexical vs. multilingual semantic retrieval — 9 November 2026

**Decision: keep lexical alias retrieval as the deployed default.** The tested
semantic candidate substantially improves this synthetic challenge set, but its
standalone worker used about 556 MiB peak RSS on this Windows machine. Render's
[free web-service plan](https://render.com/docs/compute-plans) provides 512 MB for
the entire backend. Linux/container measurements may differ; this result is
insufficient evidence that the model plus application and concurrent work fit.
No hosting upgrade, external embedding service or production model switch was
performed. The candidate is available behind the same `Embeddings` interface
for explicit offline benchmarking only.

## Paired results

Both candidates used identical corpora, questions, relevance labels, 700-character
chunks, 100-character overlap and cosine ranking. Model generation was not run.
The quality dataset's repeated style variants were deduplicated: 126 rows become
42 distinct retrieval cases. The new challenge was authored before comparison,
with 16 rental passages per source language, six topics, direct/paraphrased
questions, and all EN/DE/ES query/source combinations. Labels are synthetic,
not independently human-reviewed.

| Dataset | Queries | Lexical top-1 | Semantic top-1 | Lexical recall@4 | Semantic recall@4 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Existing RAG fixtures | 9 | 100% | 100% | 100% | 100% |
| Existing quality fixtures, deduplicated | 42 | 88.1% | 92.9% | 100% | 100% |
| New multilingual challenge | 108 | 26.9% | 87.0% | 57.4% | 98.1% |
| Challenge cross-language subset | 72 | 23.6% | 86.1% | 54.2% | 97.2% |
| All distinct cases | 159 | 47.2% | 89.3% | 71.1% | 98.7% |

The semantic candidate improved rank on 79 cases, worsened it on 10 and tied on
70. Overall MRR was 0.615 vs. 0.941. Median warm query-embedding plus ranking time
was 0.38 ms vs. 7.94 ms; p95 was 0.64 ms vs. 12.25 ms. These are local CPU
measurements, not hosted response-time or billing estimates. Separate worker
processes measured about 61 MiB vs. 556 MiB peak RSS; the measurement includes
each worker and its imports, not just model weights. Model files total 127.5 MB
on disk. No paid provider calls were made; inference is local.

Small corpora can make recall@4 trivial: only 117/159 cases have more than four
chunks. The lexical candidate had 16 tied top scores, broken by source order and
reported explicitly. Translated/paraphrased cases remain correlated; these
numbers are descriptive, not significance estimates or broad accuracy claims.
This comparison does not measure partner responses, goal scoring or usefulness.

## Candidate and reproducibility

The model is
[sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2),
Apache-2.0, pinned at `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`.
The unsigned-int8 AVX2 ONNX export produces 384-dimensional vectors with masked
mean pooling and L2 normalization. Its 128-token limit follows the model's
sentence-transformer configuration; no evaluated input was truncated. It is a
specific quantized candidate, not a benchmark of all multilingual models.

Testing discovered that dynamic int8 activation quantization changes vectors
with batch composition. Inference now handles one text at a time, and a local
integration test verifies agreement between query and document encoding. The
recorded comparison was rerun after that fix. This limits throughput and is
part of the measured trade-off, not silently assumed equivalence to full precision.

Install the existing locked Python dependencies, then run:

```powershell
python scripts/download_embedding_model.py
python scripts/compare_embeddings.py --output .runtime/embedding-comparison.json
```

The first command explicitly downloads about 128 MB of public model/tokenizer
data, enforcing pinned sizes and SHA-256 digests. No remote Python or pickle is
loaded. The second command requires verified local files, makes no downloads or
provider calls, and measures candidates in separate processes. Model files stay
in ignored `.runtime`, outside the repository. Loading the application does not
load or download this model.

[Raw paired results](../evaluation/embedding-comparison-2026-11-09.json) include
per-query rankings, language groups, timings, truncation counts, model revision,
and data/source fingerprints.
[Challenge labels](../evaluation/retrieval-challenge.json) and
[model manifest](../evaluation/embedding-model.json) are version controlled.

## Before selecting an upgrade

Measure a smaller model or run the complete application in a deployment-like
Linux container with a defined memory/concurrency allowance. Then review the
regressions with fluent humans and evaluate downstream answer support on the
same corpus. Changing retrieval or quantization requires rerunning the paired
comparison; increasing hosting cost or sending sources externally is a separate
decision. Existing semantic-quality and human-review limitations still apply.

The final paired comparison was run twice after the determinism fix: all 159
query ranks reproduced exactly for each encoder. Timing and memory varied with
machine load, as expected; the table and report use the final recorded run.
