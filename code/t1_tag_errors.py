#!/usr/bin/env python3
"""
Task 1: tag validation items whose CER exceeds 0.20 with the failure category that best explains
the error.

The task description assumes listening to each item by ear; this environment has no audio
playback, so this script makes the same judgement from the signal metrics.py already computes for
every item (its Whisper hypothesis transcript, the audio sanity stats, and SIM), applied with a
transparent, fixed set of rules -- not guessed, and fully reproducible. Each decision is printed
with the numbers behind it so it can be spot-checked (ideally still against the audio by ear before
the final submission).

Usage (after running metrics.py on the baseline validation audio with --csv):

    python metrics.py data/baseline_val --csv baseline_val_scores.csv
    python code/t1_tag_errors.py baseline_val_scores.csv

Writes predictions/t1_val_errors.csv (item_id,category) for every item with cer > --threshold,
using these rules in order:
  1. failed item (missing/unreadable/sanity-check failure) -> tag from the failure reason
     (silence-heavy or too-slow -> skipped_words; too-fast or over-duration -> repeated_words;
     anything else -> other)
  2. hypothesis much shorter than the spoken reference (length ratio < 0.70) -> skipped_words
  3. hypothesis much longer than the spoken reference (length ratio > 1.30) -> repeated_words
  4. SIM notably low for this run (sim < --sim-threshold) -> speaker_mismatch
  5. category == 'hard' (numbers/dates/amounts/abbreviations) -> number_error
  6. category == 'hinglish' (embedded English words) -> english_word_error
  7. otherwise -> other
"""
import argparse
import csv
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT))
from metrics import canon, alternatives  # noqa: E402  (pure text+numpy, no heavy deps)


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def best_ref_len(spoken: str, hyp_canon: str) -> int:
    alts = alternatives(spoken)
    if not alts:
        return 0
    # the reference alternative closest in length to the hypothesis, consistent with how cer()
    # already picks the closest-matching alternative for scoring
    return min((len(canon(a)) for a in alts), key=lambda L: abs(L - len(hyp_canon)))


def tag_item(row: dict, val_items: dict, sim_threshold: float) -> tuple[str, str]:
    """Return (tag, reason) for one scored row."""
    item = val_items[row["id"]]
    if row.get("failed") in ("True", "1", True):
        reasons = row.get("reasons", "")
        if "silence" in reasons or "speaking rate" in reasons and "outside" in reasons and "slow" in reasons.lower():
            return "skipped_words", f"failed item, reasons={reasons!r}"
        if "duration" in reasons or "clipping" in reasons:
            return "repeated_words", f"failed item, reasons={reasons!r}"
        return "other", f"failed item, reasons={reasons!r}"

    hyp_c = canon(row.get("hyp", ""))
    ref_len = best_ref_len(item["spoken"], hyp_c)
    ratio = (len(hyp_c) / ref_len) if ref_len else 1.0
    sim = float(row.get("sim", 0) or 0)

    if ratio < 0.70:
        return "skipped_words", f"hyp/ref length ratio={ratio:.2f} (hyp much shorter)"
    if ratio > 1.30:
        return "repeated_words", f"hyp/ref length ratio={ratio:.2f} (hyp much longer)"
    if sim < sim_threshold:
        return "speaker_mismatch", f"sim={sim:.3f} < threshold {sim_threshold}"
    if item["category"] == "hard":
        return "number_error", "category=hard, no stronger signal; numbers/dates/amounts are this category's defining content"
    if item["category"] == "hinglish":
        return "english_word_error", "category=hinglish, no stronger signal; embedded English words are this category's defining content"
    return "other", "no specific signal matched"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scores_csv", help="per-item CSV written by metrics.py --csv")
    ap.add_argument("--items", default=str(KIT / "data" / "val_items.csv"))
    ap.add_argument("--threshold", type=float, default=0.20)
    ap.add_argument("--sim-threshold", type=float, default=0.75)
    ap.add_argument("--out", default=str(KIT / "predictions" / "t1_val_errors.csv"))
    a = ap.parse_args()

    val_items = {r["id"]: r for r in read_csv(a.items)}
    rows = read_csv(a.scores_csv)

    tagged = []
    for row in rows:
        cer = float(row.get("cer", 0) or 0)
        if cer <= a.threshold:
            continue
        tag, reason = tag_item(row, val_items, a.sim_threshold)
        tagged.append((row["id"], tag))
        print(f"{row['id']:<12} cer={cer:.3f} sim={float(row.get('sim', 0) or 0):.3f} "
              f"cat={row['category']:<9} -> {tag:<20} ({reason})")

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["item_id", "category"])
        w.writerows(tagged)
    print(f"\nWrote {len(tagged)} tags to {out}")
    print("NOTE: these tags come from an automated heuristic (word-count ratio, SIM, item "
          "category), not from listening -- see this script's docstring. Spot-check a few against "
          "the audio by ear before submitting if at all possible.")


if __name__ == "__main__":
    main()
