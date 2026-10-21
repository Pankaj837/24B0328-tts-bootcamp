Q1 Lower CER: val_hd_08 (0.603->0.064) -- Task 2 converts the ₹ amount/date the baseline misreads
as nonsense digit sounds. val_hg_01 (0.452->0.129) -- Task 3 transliterates "office/internet/slow"
to Devanagari the model already pronounces correctly. Higher: val_hi_05 (0.000->0.020) and
val_hi_06 (0.027->0.041), both plain Hindi with no digits/English words, so neither fix touches
their input text -- the tiny rise is synthesis/ASR noise, not a real regression.

Q2 SIM barely moved (0.830->0.838) while overall CER dropped 73% -- the model already clones
voice and rhythm well; its failures are almost entirely about which phonemes it produces, not how
it sounds. I'd spend less effort on prompt/voice tuning and more on text representation, since
that was clearly the real bottleneck. I'd also test transliteration rules against more than 6
words before trusting them -- a few (e.g. "movie") still have irregular vowels no rule predicts.

Q3 Dig into the hard category specifically: at CER 0.099 it's now the single worst category,
despite Task 2 fixing the obvious number-reading. I'd listen to the remaining hard items by ear to
check whether the leftover errors are genuine mispronunciation (a normalize() gap) or just ASR
struggling with number-dense speech, since that distinction decides whether the next fix is a
text-frontend tweak or not worth chasing further.
