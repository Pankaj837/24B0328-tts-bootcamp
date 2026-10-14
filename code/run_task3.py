#!/usr/bin/env python3
"""
Task 3: synthesize validation + evaluation audio for the idea system (rule-based English->
Devanagari transliteration of hinglish text, code/translit.py), on top of Task 2's number
normalizer (code/normalize.py). Requires a GPU session with baseline/requirements.txt installed
and HF_TOKEN set (same as any other baseline/tts.py run).

Produces, with the SAME seed/decoding settings as the baseline (no overrides -- the idea only
changes the text, not decoding):
  predictions/val_control/   24 validation items, Task 2 text only (normalize(), no translit)
  predictions/val_idea/      24 validation items, Task 2 + Task 3 text (normalize() then translit_text())
  predictions/t3_idea/       40 evaluation items, Task 2 + Task 3 text

val_control/ isolates Task 3's own contribution on top of Task 2 (so the organizers -- and
results.json's val_control_cer -- can separate "normalization helped" from "transliteration helped").

Usage:
    python code/run_task3.py --seed 0
"""
import argparse
import csv
import sys
import time
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT))
sys.path.insert(0, str(KIT / "code"))

from normalize import normalize  # noqa: E402
from translit import translit_text  # noqa: E402
from baseline.tts import get_engine, save_wav  # noqa: E402


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def synth_set(engine, items, prompts, text_fn, out_dir: Path, seed: int):
    out_dir.mkdir(parents=True, exist_ok=True)
    per_item, total = {}, 0.0
    for i, it in enumerate(items, 1):
        p = prompts[it["prompt_id"]]
        text = text_fn(it["text"])
        t0 = time.time()
        y = engine(text, p["path"], p["transcript"], seed=seed)
        dt = time.time() - t0
        total += dt
        save_wav(out_dir / f"{it['id']}.wav", y)
        per_item[it["id"]] = round(dt, 3)
        print(f"  [{i}/{len(items)}] {it['id']}: {dt:.2f}s  text={text[:60]}", flush=True)
    return total, per_item


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--val-items", default=str(KIT / "data" / "val_items.csv"))
    ap.add_argument("--eval-items", default=str(KIT / "data" / "eval_items.csv"))
    ap.add_argument("--prompts", default=str(KIT / "data" / "prompts.csv"))
    ap.add_argument("--out", default=str(KIT / "predictions"))
    a = ap.parse_args()

    val_items = read_csv(a.val_items)
    eval_items = read_csv(a.eval_items)
    pbase = Path(a.prompts).resolve().parent
    prompts = {r["prompt_id"]: dict(r, path=str(pbase / r["file"])) for r in read_csv(a.prompts)}
    out = Path(a.out)

    def control_text(t):
        return normalize(t)

    def idea_text(t):
        return translit_text(normalize(t))

    engine = get_engine()
    print("warm-up...")
    engine("नमस्ते, यह एक छोटा सा परीक्षण है।", prompts[val_items[0]["prompt_id"]]["path"],
           prompts[val_items[0]["prompt_id"]]["transcript"], seed=a.seed)

    print("\n== val_control/ (Task 2 text only) ==")
    c_total, c_per = synth_set(engine, val_items, prompts, control_text, out / "val_control", a.seed)

    print("\n== val_idea/ (Task 2 + Task 3 text) ==")
    v_total, v_per = synth_set(engine, val_items, prompts, idea_text, out / "val_idea", a.seed)

    print("\n== t3_idea/ (Task 2 + Task 3 text, evaluation items) ==")
    e_total, e_per = synth_set(engine, eval_items, prompts, idea_text, out / "t3_idea", a.seed)

    import json
    timing = {"seed": a.seed, "val_control_s": round(c_total, 3), "val_idea_s": round(v_total, 3),
              "t3_idea_s": round(e_total, 3), "val_control_per_item_s": c_per,
              "val_idea_per_item_s": v_per, "t3_idea_per_item_s": e_per}
    (out / "task3_timing.json").write_text(json.dumps(timing, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\nDone. val_control/ ({len(val_items)} files), val_idea/ ({len(val_items)} files), "
          f"t3_idea/ ({len(eval_items)} files) written under {out}.")
    print("Next: python metrics.py predictions/val_control --json val_control.json --csv val_control.csv")
    print("      python metrics.py predictions/val_idea --json val_idea.json --csv val_idea.csv")
    print("      fill task3.val_cer / val_control_cer / val_cer_targeted / val_sim into results.json")


if __name__ == "__main__":
    main()
