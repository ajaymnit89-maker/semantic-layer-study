"""Run the experiment: every context mode x model x repeat on the gold set.

Each (mode, model, repeat) run is saved as its own CSV in results/raw/, so an
interrupted experiment can resume where it stopped and nothing is overwritten.

Run:  uv run python -m semantic_layer_study.run --models claude-haiku-5-5 --repeats 3
"""

import argparse
from pathlib import Path

from transit_sql.context import MODES
from transit_sql.evaluate import evaluate

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "results" / "raw"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--models", nargs="+", default=["claude-haiku-5-5"])
    p.add_argument("--modes", nargs="+", default=list(MODES), choices=MODES)
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--ids", nargs="*", help="only these question ids (for a cheap pilot)")
    args = p.parse_args()

    # A subset run goes to results/pilot/ so it is never mistaken for (and never
    # blocks) a finished full run in results/raw/.
    out_dir = ROOT / "results" / "pilot" if args.ids else RAW
    out_dir.mkdir(parents=True, exist_ok=True)
    for model in args.models:
        for rep in range(1, args.repeats + 1):
            for mode in args.modes:
                out = out_dir / f"{model}__{mode}__r{rep}.csv"
                if out.exists():
                    print(f"skip {out.name} (done)")
                    continue
                print(f"\n=== {model} | {mode} | repeat {rep}")
                df = evaluate(mode, model, args.ids)
                df["repeat"] = rep
                df.to_csv(out, index=False)
                print(f"accuracy {df.correct.mean():.1%}")


if __name__ == "__main__":
    main()
