# Semantic-layer study: study guide

This is your first research project. This guide explains the research method so you can defend it to a professor or an admissions committee.

## 1. What makes this "research" and not just a project

| A project says | A study says |
|---|---|
| "I built a chatbot that answers transit questions." | "Adding metric definitions to the prompt raised accuracy from X% to Y% (p < 0.01), mostly on ratio metrics." |
| Shows it works on a few examples | Compares conditions on the same fixed question set, repeated, with statistics |
| Hides failures | Classifies every failure and reports limitations |

## 2. The design in one paragraph

Same 32 questions, same pipeline, same models. The only thing that changes is how much the model is told about the data (four nested conditions). Because every question is answered under every condition, each question is its own control. That is a **within-subject** design, and it is why we use a **paired** test (McNemar) instead of comparing two averages.

## 3. The statistics you need

- **Accuracy** = correct answers / total answers.
- **Wilson 95% interval**: the range the true accuracy probably lies in. With 96 answers (32 questions × 3 repeats) the interval is roughly ±9 points, which is why we report it rather than one number.
- **McNemar's exact test**: looks only at the pairs where the two conditions disagree. If `semantic` is right and `raw_schema` wrong on 20 pairs, and the reverse on 3, that imbalance is very unlikely by chance. `mcnemar_exact()` in `analyze.py` computes it with the binomial distribution; read the 8 lines.
- **Repeats**: Claude doesn't give identical output every time, so we run each condition 3 times. Report the mean and the spread.

## 4. Your manual work (the part only you can do)

1. **Label failures.** After `analyze`, open `results/failures_to_label.csv` and fill `error_type` with one of the 8 categories. This error taxonomy is often the most cited part of papers like this.
2. **Grow the gold set** to 45–60 questions. Write questions an MTA operations manager would really ask. Tag each one.
3. **Freeze before you look.** Once you've seen results, don't edit the semantic layer to fix specific failures without saying so. Put new questions in a held-out set.

## 5. Related work to read (week 1–2)

Search Google Scholar for these and read abstract, figures and conclusion first:

- Spider (Yu et al., 2018) and BIRD (Li et al., 2023): the main text-to-SQL benchmarks. BIRD adds "external knowledge" hints, which is close to your semantic layer idea.
- Papers on "semantic layer LLM" or "LLM business intelligence" from dbt Labs, AtScale, and data.world, plus any academic follow-ups.
- Work on LLMs in public transit or operations analytics (try TRB / Transportation Research Record).

For each paper, note one line: what they did, and how your study differs (real public-agency KPIs, semantic layer as the manipulated variable, cost analysis).

## 6. How to talk about it

**SOP sentence (draft):** "Working on paratransit performance reporting at the MTA, I saw that the hard part of analytics is not SQL but shared metric definitions. I designed a study testing whether giving LLMs a BI semantic layer improves their accuracy on real transit KPIs, and found ..."

**To a professor (email):** one line on who you are, one on the finding with the number, one on why it relates to *their* paper, link to the preprint, a specific question.

**Interview question: "What would you do next?"**
Generate the semantic layer automatically from an existing Power BI/dbt model; test on a second agency's data; compare with retrieval-based context; study how analysts verify LLM answers (a human-in-the-loop study fits IS programs well).
