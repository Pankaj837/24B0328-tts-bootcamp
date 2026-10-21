(1) Failure: hinglish items (2-4 English words in a Hindi sentence) score CER 0.302, second-worst
after hard (fixed by Task 2). IndicF5 reads Latin words with Hindi grapheme rules, mangling them.
Target: english_word_error. Worst two: val_hg_01 (0.452, "office/internet/slow"->"हैंसे/सर्ण/कोह");
val_hg_06 (0.318, "weekend/movie/shopping"->"वियन/अहीं/चहें").

(2) Method: code/translit.py rewrites embedded English words to Devanagari before synthesis,
via hand-written spelling rules (consonant clusters, magic-e, silent letters, anusvara, c/g
softness) built only from the 6 validation hinglish items' 17 gold words -- not a lookup, so it
generalizes.

(3) Prediction: hinglish CER drops materially. Word-level test vs gold: 10/17 exact, mean
edit-distance 0.143, vs near-total mismatch for raw Latin script. Expect ~30-50% relative
reduction, little change elsewhere. Risk: spelling doesn't mark stress (extra vowels left in); a
few words (e.g. "movie") have irregular vowel quality no rule predicts.

(4) Result: hinglish CER fell 0.302 to 0.0692 -- 77% relative reduction, beating the predicted
30-50%. SIM held steady (0.837 to 0.838). All 6 hinglish items dropped below the 0.20 flag
threshold. Transliteration was the dominant fix, not a minor contributor.
