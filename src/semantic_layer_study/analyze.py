"""Turn raw run CSVs into the paper's tables and figure.

Outputs (results/):
  accuracy_by_mode.csv     accuracy per model x mode with 95% Wilson interval
  accuracy_by_tag.csv      accuracy per model x mode x question tag
  paired_tests.csv         exact McNemar test, each mode vs raw_schema, per (question, repeat)
                           and per question (majority vote over repeats)
  cost.csv                 tokens and estimated dollars per model x mode
  failures_to_label.csv    every wrong answer, with an empty error_type column
  accuracy_by_mode.png     the headline figure

Run:  uv run python -m semantic_layer_study.analyze
"""

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from transit_sql.context import MODES

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "results" / "raw"
OUT = ROOT / "results"

# $ per 1M tokens (input, output). Update if prices change.
PRICES = {
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-opus-5-5": (4.00, 20.00),
}

ERROR_TYPES = [
    "wrong_metric_definition",  # e.g. AVG of percentages instead of ratio of sums
    "missing_or_wrong_filter",  # e.g. no OTP standard filter, wrong year
    "wrong_table_or_join",
    "time_logic",               # partial year, "last year", weekday logic
    "answered_unanswerable",    # should have declined
    "declined_answerable",
    "sql_error",
    "other",
]


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (math.nan, math.nan)
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (centre - half, centre + half)


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value from the discordant pair counts."""
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2**n
    return min(1.0, 2 * tail)


def load() -> pd.DataFrame:
    files = sorted(RAW.glob("*.csv"))
    if not files:
        raise SystemExit(f"No runs in {RAW}. Run semantic_layer_study.run first.")
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    df["mode"] = pd.Categorical(df["mode"], MODES, ordered=True)
    return df


def paired_tests(df: pd.DataFrame) -> list[dict]:
    """Exact McNemar, each mode vs raw_schema, at two units of analysis.

    unit=question_repeat pairs every (question, repeat); repeats of one question are
    correlated, so this overstates n. unit=question takes the majority vote over
    repeats (ties count as wrong) and pairs questions only: the conservative test.
    """
    rows = []
    for model, g in df.groupby("model"):
        wide = g.pivot_table(index=["id", "repeat"], columns="mode", values="correct", observed=True)
        by_q = wide.groupby(level="id").mean() > 0.5
        for unit, w in [("question_repeat", wide), ("question", by_q)]:
            for mode in MODES[1:]:
                if mode not in w or "raw_schema" not in w:
                    continue
                base, other = w["raw_schema"].astype(bool), w[mode].astype(bool)
                b, c = int((other & ~base).sum()), int((base & ~other).sum())
                rows.append({"model": model, "unit": unit, "n": len(w), "mode": mode, "vs": "raw_schema",
                             "only_mode_correct": b, "only_baseline_correct": c,
                             "p_value": round(mcnemar_exact(b, c), 4)})
    return rows


def main() -> None:
    df = load()

    by_mode = df.groupby(["model", "mode"], observed=True).correct.agg(["sum", "count"]).reset_index()
    by_mode["accuracy"] = by_mode["sum"] / by_mode["count"]
    by_mode[["ci_low", "ci_high"]] = [wilson(k, n) for k, n in zip(by_mode["sum"], by_mode["count"])]
    by_mode.round(3).to_csv(OUT / "accuracy_by_mode.csv", index=False)
    print(by_mode.round(3).to_string(index=False))

    tags = df.assign(tag=df.tags.str.split(",")).explode("tag")
    (tags.pivot_table(index=["model", "tag"], columns="mode", values="correct", aggfunc="mean", observed=True)
         .round(2).to_csv(OUT / "accuracy_by_tag.csv"))

    pd.DataFrame(paired_tests(df)).to_csv(OUT / "paired_tests.csv", index=False)

    cost = df.groupby(["model", "mode"], observed=True)[["input_tokens", "output_tokens"]].sum().reset_index()
    cost["usd"] = [
        (i * PRICES.get(m, (0, 0))[0] + o * PRICES.get(m, (0, 0))[1]) / 1e6
        for m, i, o in zip(cost.model, cost.input_tokens, cost.output_tokens)
    ]
    cost.round(4).to_csv(OUT / "cost.csv", index=False)
    print(f"\nTotal estimated cost: ${cost.usd.sum():.2f}")

    fails = df[~df.correct.astype(bool)].copy()
    fails["error_type"] = ""
    fails[["id", "model", "mode", "repeat", "tags", "error", "sql", "notes", "error_type"]].to_csv(
        OUT / "failures_to_label.csv", index=False)
    print(f"{len(fails)} failures written for labeling. Allowed error_type values: {', '.join(ERROR_TYPES)}")

    fig, ax = plt.subplots(figsize=(7, 4))
    models = list(by_mode.model.unique())
    width = 0.8 / len(models)
    for i, model in enumerate(models):
        m = by_mode[by_mode.model == model].set_index("mode").reindex(MODES)
        x = [j + i * width for j in range(len(MODES))]
        ax.bar(x, m.accuracy * 100, width,
               yerr=[(m.accuracy - m.ci_low) * 100, (m.ci_high - m.accuracy) * 100],
               capsize=3, label=model)
    ax.set_xticks([j + width * (len(models) - 1) / 2 for j in range(len(MODES))], MODES)
    ax.set_ylabel("Execution accuracy (%)")
    ax.set_ylim(0, 100)
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "accuracy_by_mode.png", dpi=200)
    print(f"Saved figures and tables to {OUT}")


if __name__ == "__main__":
    main()
