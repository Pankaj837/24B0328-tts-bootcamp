# Reproduction commands

AI assistant disclosure: this submission's code, text frontend, and transliteration rules were
developed with Claude (Anthropic) as a coding assistant, working interactively with me in this
repository. idea.md and report.md are my own words and judgement calls, not generated text.

Run everything from the kit root. Steps marked **[GPU]** need a CUDA session with
`baseline/requirements.txt` installed and `HF_TOKEN` set (IndicF5 terms accepted at
huggingface.co/ai4bharat/IndicF5); they were run on Kaggle/Colab, not this machine — see
`RUN_ON_KAGGLE.md` for the exact session log/commands. Steps without the tag are plain Python, no
extra installs, and were run locally.

## Task 1 — measure the baseline

```bash
python metrics.py data/baseline_val --json baseline_val_scores.json --csv baseline_val_scores.csv   # [GPU]
python code/t1_tag_errors.py baseline_val_scores.csv                                                 # [GPU session, light]
```
`code/t1_tag_errors.py` tags every item with CER > 0.20 using an automated heuristic (hypothesis/
reference word-count ratio, SIM, item category) over metrics.py's own per-item output, since this
environment has no audio playback — see the script's docstring for the exact rule order and
reasoning printed per item. Writes `predictions/t1_val_errors.csv`.

## Task 2 — text frontend

```bash
python code/make_t2_normalized.py   # writes predictions/t2_normalized.csv, self-checks vs validation 'spoken'
python baseline/run_baseline.py --items data/eval_items.csv --out predictions/t2_norm \
    --text-csv predictions/t2_normalized.csv --text-column normalized_text                           # [GPU]
```
`code/normalize.py` is the rule-based `normalize(text)`: Indian-system number-to-words (crore/lakh/
hazar), dates (`DD/MM/YYYY` and "D &lt;month&gt; YYYY"), ₹ amounts (plain, with a lakh/crore/hazar unit
word, with paise for decimals), generic decimals ("दशमलव", digit-by-digit), and all-caps
abbreviations spelled out letter by letter (RBI, GST, ATM, ...). Verified: all 8 validation 'hard'
items normalize to an exact character match against `spoken` (text_cer = 0.000).

## Task 3 — the idea

```bash
python code/run_task3.py --seed 0                                                                    # [GPU]
python metrics.py predictions/val_control --json val_control.json --csv val_control.csv              # [GPU]
python metrics.py predictions/val_idea --json val_idea.json --csv val_idea.csv                       # [GPU]
```
`code/translit.py` is the rule-based `translit_text(text)`: transliterates English words embedded in
hinglish text to Devanagari using hand-written spelling-pattern rules (onset/coda consonant clusters,
magic-e vowel lengthening, silent letters, anusvara before stop consonants, c/g softness), built only
from the 6 validation hinglish items' 17 gold English-word transliterations — not a lookup table.
Measured against those 17 words: 10/17 exact matches, mean character edit-distance 0.143 (see
idea.md for the honest accounting of the rest). `code/run_task3.py` applies
`translit_text(normalize(text))` and writes `predictions/val_idea/` and `predictions/t3_idea/`, plus
`predictions/val_control/` (`normalize(text)` alone, baseline otherwise) so Task 3's own contribution
can be separated from Task 2's.

## Task 4 — speed (optional)

```bash
python baseline/run_baseline.py --items data/val_items.csv --out out/baseline_val                    # [GPU]
```
[fill in once run: the fast variant's command and `predictions/t4_fast/`]

## Development-only checks (no GPU, no models)

```bash
python code/make_t2_normalized.py          # Task 2 self-check against validation ground truth
python check_format.py .                  # validates the submission layout before zipping
```
