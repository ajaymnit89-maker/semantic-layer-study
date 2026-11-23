# Does a BI semantic layer make LLM analytics more accurate?

An empirical study of large language models writing SQL for public transit performance questions, using MTA NYC Transit paratransit (Access-A-Ride) open data.

**Status:** design done, gold set v1 (32 questions) done, pilot runs pending.
**Author:** Ajay Sharma. Code for the assistant under test: [`../transit-sql`](../transit-sql).

## Motivation

Business intelligence teams spend years defining metrics so that everyone computes "on-time performance" the same way. In Power BI or a dbt/Looker stack, those definitions live in a semantic layer. LLM "chat with your data" tools usually skip this layer and hand the model raw table schemas. The model then has to guess the business logic.

Transit operations data makes the guesswork visible. A few examples from this dataset:

- Pickup on-time performance must be computed as on-time pickups divided by total pickups. Averaging daily percentages gives a different, wrong number.
- The OTP table lists every trip once per standard (15, 20 and 30 minutes). Summing pickups without picking a standard triples the count.
- Provider no-shows are published as a rate per 1,000 trips. Summing that column is meaningless.
- The complaint rate needs complaints and trips from two tables, each aggregated to the same period before dividing.

None of this is visible from column names alone.

## Research questions

- **RQ1.** How much does adding a semantic layer (metric definitions and business rules) to the prompt improve LLM text-to-SQL accuracy on operational transit questions, compared with a raw schema or a data dictionary?
- **RQ2.** Which kinds of questions benefit most: ratio metrics, filters required by business rules, cross-table rates, time logic, or questions the data cannot answer?
- **RQ3.** How does the effect change with model size and cost? Can a small model plus a semantic layer match a large model without one?

## Hypotheses

- **H1.** Accuracy rises from raw schema → data dictionary → semantic layer.
- **H2.** The largest gains are on `ratio_of_sums`, `otp_standard` and `rate_not_count` questions. Basic questions gain little.
- **H3.** The semantic layer narrows the gap between small and large models.

## Design

| Element | Choice |
|---|---|
| Data | 5 tables aggregated from 8 MTA datasets on data.ny.gov; frozen at 2016-10-01 to 2026-09-30 |
| Conditions (within-subject) | `raw_schema`, `schema_dict`, `semantic`, `semantic_fewshot`; each adds to the previous, see `transit-sql/src/transit_sql/context.py` |
| Models | Claude Haiku 5.5, Claude Sonnet 5.5, Claude Opus 5.5 (cost permitting) |
| Questions | 32 gold questions in `transit-sql/evals/gold_questions.yaml`, tagged by difficulty type; 2 are unanswerable |
| Repeats | 3 per condition (model sampling is not deterministic) |
| Pipeline | identical for all conditions: one structured-output call, one repair attempt on SQL error |
| Metric | execution accuracy: the result set must contain the gold result (column names and order ignored, numbers within rounding tolerance); unanswerable items must be declined |
| Statistics | 95% Wilson intervals; exact McNemar test on paired (question, repeat) outcomes vs. `raw_schema` |
| Error analysis | every failure hand-labeled into 8 categories (see `analyze.py`) |
| Cost | input/output tokens per call, converted to dollars |

## How to run

1. Nothing to set up if the `claude` command (Claude Code) is logged in with your Claude subscription: runs go through it. To use the paid API instead, put a key in `../transit-sql/.env`. Use the same backend for every run in one comparison, and note it in the paper.
2. Pilot on 5 questions to check everything works (costs cents):
   ```
   uv run python -m semantic_layer_study.run --models claude-haiku-5-5 --repeats 1 --ids q01 q08 q17 q24 q31
   ```
3. Full run, Haiku first (about $0.15 for 384 calls):
   ```
   uv run python -m semantic_layer_study.run --models claude-haiku-5-5 --repeats 3
   ```
   Then add `claude-sonnet-5-5` (about $3) and `claude-opus-5-5` (about $5–6). Finished runs are skipped, so you can stop and resume.
4. Build the tables and figure:
   ```
   uv run python -m semantic_layer_study.analyze
   ```
5. Label `results/failures_to_label.csv` by hand (column `error_type`).

## Threats to validity

- **Small benchmark.** 32 questions written by one person who knows the data. Mitigation: grow the set to 60+, and ask 2–3 analysts to write questions blind.
- **Author bias.** The same person wrote the semantic layer and the questions, so the layer may cover exactly what the questions test. Mitigation: freeze the layer before writing new questions, and report results on the held-out new questions separately.
- **One domain, one model family.** Results may not transfer. A second dataset (e.g. MTA subway or bus metrics) or another provider's model would help.
- **Lenient scoring.** Extra columns are allowed, so a model could pass by returning many columns. Spot-check passes.

## Planned write-up

A 6–8 page paper: introduction, related work (text-to-SQL benchmarks such as Spider and BIRD, semantic layers, LLMs for analytics), data and benchmark, method, results (RQ1–RQ3), error analysis, limitations. Target: arXiv/SSRN preprint, then a workshop or a conference in IS or transportation (e.g. TRB Annual Meeting, AMCIS, a KDD/ACL workshop on data science or tabular data).

## Timeline

| Week | Work |
|---|---|
| 1 | Pilot run; fix scoring edge cases; grow gold set to 45 |
| 2 | Full Haiku + Sonnet runs; label failures |
| 3 | Opus run; second question writer; held-out set |
| 4 | Draft paper; figures |
| 5 | Revise; post preprint; email professors with the link |

## Repository layout

```
src/semantic_layer_study/run.py      runs modes x models x repeats, saves results/raw/*.csv
src/semantic_layer_study/analyze.py  accuracy tables, paired tests, cost, failure sheet, figure
tests/                               offline tests for the statistics and analysis
```
