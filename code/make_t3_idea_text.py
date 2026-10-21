#!/usr/bin/env python3
"""
Task 4 prep: materialize translit_text(normalize(text)) for all 64 items as a CSV, so the Task 3
idea's text transform can be fed to baseline/run_baseline.py's --text-csv for a fast-decoding
variant (Task 4), reusing its existing timing/CLI machinery instead of a bespoke script.

This is the exact same text run_task3.py computes internally for val_idea/ and t3_idea/ -- just
written out here so it can be combined with --set nfe_step=... for Task 4.

    python code/make_t3_idea_text.py
"""
import csv
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT))
sys.path.insert(0, str(KIT / "code"))

from normalize import normalize  # noqa: E402
from translit import translit_text  # noqa: E402


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    val_items = read_csv(KIT / "data" / "val_items.csv")
    eval_items = read_csv(KIT / "data" / "eval_items.csv")

    out_path = KIT / "predictions" / "t3_idea_text.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "text"])
        for it in val_items + eval_items:
            w.writerow([it["id"], translit_text(normalize(it["text"]))])
    print(f"Wrote {len(val_items) + len(eval_items)} rows to {out_path}")


if __name__ == "__main__":
    main()
