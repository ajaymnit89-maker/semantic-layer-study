import random

import pandas as pd
import pytest

from semantic_layer_study import analyze
from transit_sql.context import MODES


def test_mcnemar_known_values():
    assert analyze.mcnemar_exact(0, 6) == pytest.approx(0.03125)
    assert analyze.mcnemar_exact(3, 3) == 1.0


def test_wilson_contains_point_estimate():
    lo, hi = analyze.wilson(30, 40)
    assert lo < 0.75 < hi


def test_analyze_end_to_end(tmp_path, monkeypatch):
    raw = tmp_path / "raw"
    raw.mkdir()
    random.seed(0)
    for i, mode in enumerate(MODES):
        rows = [{"id": f"q{q:02d}", "mode": mode, "model": "claude-haiku-5-5", "repeat": 1,
                 "tags": "basic,ratio_of_sums", "correct": random.random() < 0.4 + 0.15 * i,
                 "error": None, "input_tokens": 3000, "output_tokens": 200, "sql": "SELECT 1",
                 "notes": ""} for q in range(30)]
        pd.DataFrame(rows).to_csv(raw / f"haiku__{mode}__r1.csv", index=False)
    monkeypatch.setattr(analyze, "RAW", raw)
    monkeypatch.setattr(analyze, "OUT", tmp_path)

    analyze.main()

    for name in ["accuracy_by_mode.csv", "accuracy_by_tag.csv", "paired_tests.csv",
                 "cost.csv", "failures_to_label.csv", "accuracy_by_mode.png"]:
        assert (tmp_path / name).exists(), name
    assert len(pd.read_csv(tmp_path / "paired_tests.csv")) == 6  # 3 modes x 2 units


def test_question_level_uses_majority_vote():
    # q1: baseline wrong 3/3, semantic right 3/3. q2: baseline right 2/3, semantic right 3/3.
    base = {"q1": [0, 0, 0], "q2": [1, 1, 0]}
    rows = [{"id": q, "repeat": r + 1, "model": "m", "mode": mode, "correct": bool(v)}
            for q, vals in base.items() for r, v in enumerate(vals)
            for mode, v in [("raw_schema", v), ("semantic", 1)]]
    df = pd.DataFrame(rows)
    df["mode"] = pd.Categorical(df["mode"], MODES, ordered=True)
    tests = {t["unit"]: t for t in analyze.paired_tests(df)}
    assert (tests["question_repeat"]["n"], tests["question_repeat"]["only_mode_correct"]) == (6, 4)
    assert (tests["question"]["n"], tests["question"]["only_mode_correct"]) == (2, 1)
