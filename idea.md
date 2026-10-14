(1) Failure: hinglish items (2-4 English words in Latin script inside a Hindi sentence) score
CER 0.302 in data/baseline_published.json, second-worst after hard's number errors. IndicF5 reads
the Latin words with Hindi grapheme rules and mangles them. Target: english_word_error. Items:
val_hg_01, val_hg_03 (office/internet/slow; flight/cancel/hotel — several English words each).
[PENDING: replace with real Task 1 items]

(2) Method: code/translit.py rewrites embedded English words to Devanagari before synthesis, using
hand-written spelling-pattern rules (onset/coda consonant clusters, magic-e vowel lengthening,
silent letters, anusvara, c/g softness) built only from the 6 validation hinglish items' 17 gold
words — not a lookup table, so it generalizes to unseen English words.

(3) Prediction: hinglish CER drops materially. Word-level test against validation gold gave 10/17
exact matches (mean edit-distance 0.143) versus near-total mismatch for raw Latin script fed to a
Hindi-only reader. Expect roughly 30-50% relative CER reduction on hinglish, little change elsewhere.
Risk: English spelling doesn't mark stress, so some words keep a vowel the model still mispronounces;
a few words (e.g. "movie") have irregular vowel quality no spelling rule predicts.

(4) Result: [PENDING: run Task 3, score val_idea/]
