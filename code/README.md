# Reproduction commands

AI assistant disclosure: this submission's code, text frontend, and transliteration rules were
developed with Claude (Anthropic) as a coding assistant, working interactively with me in this
repository. idea.md and report.md's judgement calls, analysis and results are mine; Claude
rephrased the actual wording from the real numbers and decisions produced in that work, at my
direction.

Run everything from the kit root. Steps marked **[Kaggle]** were run on a Kaggle notebook (Task 1:
CPU session, no GPU/HF token needed, since `metrics.py` only uses public Whisper/ECAPA models;
Task 2-4: GPU T4 session, with `baseline/requirements.txt` installed and `HF_TOKEN` set after
accepting IndicF5's terms at huggingface.co/ai4bharat/IndicF5). Steps without the tag are plain
Python, no extra installs, and were run locally.

One known deviation, disclosed rather than hidden: `baseline/requirements.txt` pins
`git+https://github.com/ai4bharat/IndicF5.git@fb652a96...`, but that exact commit no longer exists
in the GitHub repo (`fatal: reference is not a tree`) as of this run. Installed from the repo's
current default branch instead. This only affects the inference *wrapper code*; the actual
**model weights stay correctly pinned** — that's a separate reference on Hugging Face, set in
`baseline/config.yaml`'s `revision` field and confirmed in every run's logs
(`.../snapshots/fb652a96e508091045890dae5bb99fe511facbcf/checkpoints/...`).

## Task 1 — measure the baseline

```bash
python metrics.py data/baseline_val --json baseline_val_scores.json --csv baseline_val_scores.csv   # [Kaggle]
python code/t1_tag_errors.py baseline_val_scores.csv                                                 # [Kaggle]
```
Result: overall CER 0.2409, SIM 0.8303 (matches `data/baseline_published.json` within tolerance).
`code/t1_tag_errors.py` tags every item with CER > 0.20 using an automated heuristic (hypothesis/
reference word-count ratio, SIM, item category) over metrics.py's own per-item output, since this
environment has no audio playback — see the script's docstring for the exact rule order and
reasoning printed per item. Writes `predictions/t1_val_errors.csv`.

## Task 2 — text frontend

```bash
python code/make_t2_normalized.py   # writes predictions/t2_normalized.csv, self-checks vs validation 'spoken'
python baseline/run_baseline.py --items data/eval_items.csv --out predictions/t2_norm \
    --text-csv predictions/t2_normalized.csv --text-column normalized_text                           # [Kaggle]
python baseline/run_baseline.py --items data/val_items.csv --out out/t2_val_norm \
    --text-csv predictions/t2_normalized.csv --text-column normalized_text                           # [Kaggle]
python metrics.py out/t2_val_norm --json t2_val_norm.json --csv t2_val_norm.csv                       # [Kaggle]
```
`code/normalize.py` is the rule-based `normalize(text)`: Indian-system number-to-words (crore/lakh/
hazar), dates (`DD/MM/YYYY` and "D &lt;month&gt; YYYY"), ₹ amounts (plain, with a lakh/crore/hazar unit
word, with paise for decimals), generic decimals ("दशमलव", digit-by-digit), and all-caps
abbreviations spelled out letter by letter (RBI, GST, ATM, ...). Verified: all 8 validation 'hard'
items normalize to an exact character match against `spoken` (text_cer = 0.000). On the full
validation set with normalization on: overall CER 0.2409 -> 0.1231, hard category 0.4545 -> 0.0989
(78% relative reduction), other categories essentially unchanged.

## Task 3 — the idea

```bash
python code/run_task3.py --seed 0                                                                    # [Kaggle]
python metrics.py predictions/val_control --json val_control.json --csv val_control.csv              # [Kaggle]
python metrics.py predictions/val_idea --json val_idea.json --csv val_idea.csv                       # [Kaggle]
```
`code/translit.py` is the rule-based `translit_text(text)`: transliterates English words embedded in
hinglish text to Devanagari using hand-written spelling-pattern rules (onset/coda consonant clusters,
magic-e vowel lengthening, silent letters, anusvara before stop consonants, c/g softness), built only
from the 6 validation hinglish items' 17 gold English-word transliterations — not a lookup table.
Measured against those 17 words: 10/17 exact matches, mean character edit-distance 0.143 (see
idea.md for the honest accounting of the rest). `code/run_task3.py` applies
`translit_text(normalize(text))` and writes `predictions/val_idea/` and `predictions/t3_idea/`, plus
`predictions/val_control/` (`normalize(text)` alone, baseline otherwise) so Task 3's own contribution
can be separated from Task 2's. Result: targeted category (hinglish) CER 0.302 (Task 2 text only) ->
0.0692 (Task 2 + translit), a 77% relative reduction; SIM held steady (0.837 -> 0.838).

## Task 4 — speed

```bash
python code/make_t3_idea_text.py                                                                     # writes predictions/t3_idea_text.csv (translit_text(normalize(text)) for all 64 items)
python baseline/run_baseline.py --items data/val_items.csv --out out/baseline_val                    # [Kaggle]
python baseline/run_baseline.py --items data/val_items.csv --out out/t4_fast_val \
    --text-csv predictions/t3_idea_text.csv --text-column text --set nfe_step=16                     # [Kaggle]
python metrics.py out/t4_fast_val --json t4_fast_val.json --csv t4_fast_val.csv                      # [Kaggle]
python baseline/run_baseline.py --items data/eval_items.csv --out predictions/t4_fast \
    --text-csv predictions/t3_idea_text.csv --text-column text --set nfe_step=16                     # [Kaggle]
```
The only change from Task 3 is halving `nfe_step` (32 -> 16, the flow-matching step count) via a
decoding override. Baseline and the fast variant were both timed on the same validation items, same
Kaggle GPU session, model loaded and one warm-up excluded, per the rules. Result: 575.2s -> 304.6s,
**1.89x speed-up**, fast-variant CER 0.0740, within the required 1.2x ceiling of Task 3's 0.0649
(ceiling 0.0779).

## Development-only checks (no GPU, no models)

```bash
python code/make_t2_normalized.py          # Task 2 self-check against validation ground truth
python check_format.py .                  # validates the submission layout before zipping
```
