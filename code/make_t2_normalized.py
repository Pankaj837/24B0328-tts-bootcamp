#!/usr/bin/env python3
"""
Task 2: apply normalize() to all 64 items (24 validation + 40 evaluation) and write
predictions/t2_normalized.csv (id,split,text,normalized_text).

Also prints a dev-time *text*-level sanity check (not the official audio CER): for validation
items it compares canon(normalize(text)) against canon(spoken) using metrics.py's own canon/cer
functions (no models needed, pure text) so mistakes in the frontend are visible before spending any
GPU time on synthesis.

    python code/make_t2_normalized.py
"""
import csv
import re
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT))
sys.path.insert(0, str(KIT / "code"))

from normalize import normalize  # noqa: E402
from metrics import canon, cer  # noqa: E402  (pure-python/numpy only at import time)

_LEFTOVER = re.compile(r"[0-9०-९₹%]")


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    val_items = read_csv(KIT / "data" / "val_items.csv")
    eval_items = read_csv(KIT / "data" / "eval_items.csv")

    rows = []
    for it in val_items:
        rows.append({"id": it["id"], "split": "val", "text": it["text"],
                     "normalized_text": normalize(it["text"]), "category": it["category"],
                     "spoken": it.get("spoken", "")})
    for it in eval_items:
        rows.append({"id": it["id"], "split": "eval", "text": it["text"],
                     "normalized_text": normalize(it["text"]), "category": it["category"]})

    out_dir = KIT / "predictions"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "t2_normalized.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "split", "text", "normalized_text"])
        for r in rows:
            w.writerow([r["id"], r["split"], r["text"], r["normalized_text"]])
    print(f"Wrote {len(rows)} rows to {out_path}")

    # Sanity: no digits/rupee/percent symbols should remain anywhere.
    leftovers = [r["id"] for r in rows if _LEFTOVER.search(r["normalized_text"])]
    if leftovers:
        print(f"\nWARNING: digits/₹/% still present in: {leftovers}")
    else:
        print("\nOK: no digits, ₹ or % left in any normalized_text.")

    # Dev-time text CER proxy on validation 'hard' items (where spoken is known).
    print("\nValidation 'hard' items: canon(normalize(text)) vs canon(spoken) [text-level, not audio]")
    hard = [r for r in rows if r["split"] == "val" and r["category"] == "hard"]
    total = 0.0
    for r in hard:
        c = cer(r["spoken"], r["normalized_text"])
        total += c
        flag = "" if c < 0.05 else "  <-- check this one"
        print(f"  {r['id']:<12} text_cer={c:.3f}{flag}")
        if c >= 0.05:
            print(f"      normalized: {r['normalized_text']}")
            print(f"      spoken:     {r['spoken']}")
    if hard:
        print(f"  mean text_cer over hard items: {total / len(hard):.3f}")


if __name__ == "__main__":
    main()
