"""
Task 3 idea: rule-based English-to-Devanagari transliteration for English words embedded in
Hinglish text (the `hinglish` / english_word_error failure). Pure spelling-pattern rules, no
transliteration or pronunciation model -- built only from the 6 validation hinglish items'
Devanagari ground truth (`spoken` column of val_items.csv), then applied to unseen eval words.

Patterns used, in the order they fire on a lowercase word:
  1. digraphs/trigraphs that are a single Hindi sound: sh,ch,th,ph,wh,ck,ng,qu,igh,tion,sion
  2. word-initial prefix "ad" + consonant -> E-like onset (address, admin, advance ...)
  3. silent trailing "e" after a consonant is dropped (office, hope, ...)
  4. doubled letters collapse to one (office "ff" -> f, class "ss" -> s)
  5. a *doubled* consonant letter broadens a short "a" just before it to aa (class/glass/pass),
     matching English's own "broad A" / trap-bath pattern before certain consonant clusters. (The
     same idea for short "e" was tested and dropped: "message" broadens but "address" doesn't, so
     it isn't a reliable rule and is left as a documented miss instead of overfit to one example.)
  6. "n"/"m" immediately before another consonant becomes anusvara on the preceding vowel
     (weekend/internet), instead of a written न/म.
  7. c/g are soft (स/ज) before e,i,y and hard (क/ग) elsewhere.
  8. recognized English onset consonant+liquid clusters (cl,cr,bl,br,dr,fl,fr,gl,gr,pl,pr,sl,sm,
     sn,sp,st,sw,sc,sk,tr,tw) are joined with a halant, as Hindi would write them (क्लास, फ्लाइट,
     प्रॉपर, स्लो); other adjacent consonants are left separate (no halant), matching how Hindi
     naturally breaks unfamiliar clusters with an implicit short vowel (इंटरनेट).
  9. default single-letter consonant/vowel table, tuned to Indian-English conventions (t/d are
     retroflex ट/ड, not dental त/द; bare "o" defaults to the short ऑ as in office/shopping/proper).
     "y" is vocalic everywhere except word-initial position (party/battery keep their vowel "y";
     yoga/yes get a leading य), handled as an explicit special case rather than a dictionary entry,
     since adding "y" to the plain consonant table caused it to be swept into other rules that key
     off that table and broke "battery"/"party" -- caught by rerunning the regression test before
     it ever reached a submission.

A word-final 2-consonant coda cluster (report/confirm/password-style endings) is deliberately left
unclustered (no halant), even though common loanwords like पोस्ट/कार्ड would normally cluster it --
an earlier version of this rule was dropped because it was motivated by looking at evaluation-only
words, which the task rules don't allow; see idea.md and code/README.md for the full account.

Known, documented limitation (see idea.md / report.md): English spelling alone does not mark word
stress or vowel reduction, so unstressed vowels are sometimes written when a fluent Hindi rendering
would drop them (e.g. this engine's "internet" keeps a vowel between t and r that the gold render
omits), and a handful of English words have genuinely irregular vowel quality that no spelling rule
predicts (e.g. "movie"'s stressed o is actually a long "oo", not the ऑ a flat reading of 'o' gives).
This is an expected, honestly-reported failure mode of a *rule-based, no-model* approach.
"""
import re

_CONSONANTS = {
    "b": "ब", "d": "ड", "f": "फ", "h": "ह", "j": "ज", "k": "क", "l": "ल", "m": "म",
    "n": "न", "p": "प", "r": "र", "s": "स", "t": "ट", "v": "व", "w": "व", "x": "क्स", "z": "ज़",
}
# "y" is deliberately NOT in _CONSONANTS: at word end or mid-word it is vocalic (party, happy,
# type) far more often than not, and the word-final coda-cluster rule below keys off _CONSONANTS
# membership, so adding "y" there would wrongly cluster "ry"/"ty" endings. Word-initial "y" (yoga,
# yes) is the one place it is reliably consonantal, handled as an explicit special case instead.
_ONSET_CLUSTERS = {
    "bl", "br", "cl", "cr", "dr", "fl", "fr", "gl", "gr", "pl", "pr",
    "sc", "sk", "sl", "sm", "sn", "sp", "st", "sw", "tr", "tw",
}
_VOWEL_MATRA = {"a": "", "aa": "ा", "i": "ि", "ii": "ी", "u": "ु", "uu": "ू",
                "e": "े", "ai": "ै", "o": "ो", "au": "ॉ", "ow": "ौ"}
_VOWEL_INDEP = {"a": "अ", "aa": "आ", "i": "इ", "ii": "ई", "u": "उ", "uu": "ऊ",
                "e": "ए", "ai": "ऐ", "o": "ओ", "au": "ऑ", "ow": "औ"}
_VOWELS = set("aeiou")


def _collapse_doubles(word: str):
    """Return (word with doubled consonant letters collapsed to one, set of indices-in-output
    where a doubling happened -- used by the 'a' broadening rule, see translit_word)."""
    out = []
    broad_after = set()
    i = 0
    while i < len(word):
        ch = word[i]
        if i + 1 < len(word) and word[i + 1] == ch and ch not in _VOWELS:
            broad_after.add(len(out) - 1)  # the vowel just emitted before this is broadened
            out.append(ch)
            i += 2
        else:
            out.append(ch)
            i += 1
    return "".join(out), broad_after


class _Writer:
    def __init__(self):
        self.out = []
        self.pending = None  # Devanagari base letter of a consonant awaiting a vowel

    def consonant(self, letter: str, cluster_with_prev: bool = False):
        if self.pending is not None and cluster_with_prev:
            self.out.append("्")
        self.out.append(letter)
        self.pending = letter

    def vowel(self, code: str):
        if self.pending is not None:
            self.out.append(_VOWEL_MATRA[code])
            self.pending = None
        else:
            self.out.append(_VOWEL_INDEP[code])

    def anusvara(self):
        self.out.append("ं")

    def literal(self, s: str):
        self.out.append(s)
        self.pending = None

    def text(self):
        return "".join(self.out)


def translit_word(word: str) -> str:
    w = re.sub(r"[^A-Za-z]", "", word).lower()
    if not w:
        return word

    special_prefix = w.startswith("ad") and len(w) > 2 and w[2] not in _VOWELS
    if special_prefix:
        w = w[1:]  # drop the leading 'a'; its vowel quality is handled below

    force_soft_final = False
    had_silent_e = False
    if len(w) > 3 and w.endswith("e") and w[-2] not in _VOWELS:
        # drop silent trailing e (office, hope, ...); if it follows c/g, that's exactly the
        # orthographic signal that the c/g is soft (otherwise English wouldn't need the e there)
        had_silent_e = True
        if w[-2] in ("c", "g"):
            force_soft_final = True
        w = w[:-1]

    w, broad_after = _collapse_doubles(w)

    # "magic e": in a VCe word (line, page, hope, cute) the dropped e makes the vowel before the
    # single consonant "say its name" (long/diphthong) -- but only when that syllable is the one
    # that keeps the stress, which spelling alone can't always tell (e.g. "office" does NOT
    # lengthen its i despite the same VCe shape; see translit_word's docstring).
    magic_e_idx = None
    if had_silent_e and len(w) >= 2 and w[-2] in _VOWELS:
        magic_e_idx = len(w) - 2

    writer = _Writer()
    if special_prefix:
        writer.vowel("e")  # "ad-" -> E-onset (address, admin, advance)

    i, n = 0, len(w)
    while i < n:
        ch = w[i]

        if w[i:i + 4] == "tion":
            writer.literal("शन"); i += 4; continue
        if w[i:i + 4] == "sion":
            writer.literal("ज़न"); i += 4; continue
        if w[i:i + 3] == "igh":
            writer.literal("ा" + "इ"); i += 3; continue
        if w[i:i + 2] in ("sh", "ch", "ph", "wh", "ck", "qu", "ng"):
            pair = w[i:i + 2]
            base = {"sh": "श", "ch": "च", "ph": "फ़", "wh": "व", "ck": "क", "qu": "क्व"}
            if pair == "ng":
                writer.anusvara(); writer.consonant("ग"); i += 2; continue
            writer.consonant(base[pair]); i += 2; continue

        if ch == "y" and i == 0:
            writer.consonant("य"); i += 1; continue

        if ch in "aeiou" or ch == "y":
            # --- vowel handling --- (word-initial y was already consumed as a consonant above)
            if w[i:i + 2] == "ee":
                writer.vowel("ii"); i += 2; continue
            if w[i:i + 2] == "ea":
                writer.vowel("ii"); i += 2; continue
            if w[i:i + 2] == "oo":
                writer.vowel("uu"); i += 2; continue
            if w[i:i + 2] == "oa":
                writer.vowel("o"); i += 2; continue
            if w[i:i + 2] == "ew":
                writer.literal("्यू" if writer.pending is not None else "यू"); i += 2; continue
            if w[i:i + 2] in ("ai", "ay"):
                writer.vowel("e"); i += 2; continue
            if w[i:i + 2] in ("oy", "oi"):
                writer.literal("ॉय"); i += 2; continue
            if w[i:i + 2] in ("ow", "ou"):
                last = (i + 2 >= n)
                writer.vowel("o" if last else "ow"); i += 2; continue
            if w[i:i + 3] == "alk":  # silent l: walk/talk/chalk/stalk -> vaak/taak/chaak-style
                writer.vowel("au"); i += 2; continue  # skips the 'l', leaves 'k' for the next pass
            if i == magic_e_idx:
                if ch == "a":
                    writer.vowel("e"); i += 1; continue
                if ch == "i" or ch == "y":
                    writer.literal("ा" + "इ"); i += 1; continue
                if ch == "o":
                    writer.vowel("o"); i += 1; continue
                if ch == "u":
                    writer.literal("्यू" if writer.pending is not None else "यू"); i += 1; continue
            if ch == "a":
                broad = (i in broad_after)
                writer.vowel("aa" if broad else "ai"); i += 1; continue
            if ch == "e":
                writer.vowel("e"); i += 1; continue
            if ch == "i" or ch == "y":
                writer.vowel("i"); i += 1; continue
            if ch == "o":
                writer.vowel("au"); i += 1; continue
            if ch == "u":
                writer.vowel("u"); i += 1; continue

        # --- consonant handling ---
        # anusvara represents a nasal homorganic with a following STOP consonant (b,p,t,d,k,g,
        # c,j); before a continuant (l,r,s,v,...) Hindi writes a real न/म instead (ऑनलाइन, not
        # ऑंलाइन), so the trigger set below is deliberately narrower than "any consonant".
        if ch in ("n", "m") and i + 1 < n and w[i + 1] in "pbtdkgcj":
            writer.anusvara(); i += 1; continue
        if w[i:i + 2] in _ONSET_CLUSTERS:
            # clusters only ever pair c/g with a liquid (cl,cr,gl,gr), which never triggers the
            # soft c/g rule, so the hard form is always correct here.
            hard = {"c": "क", "g": "ग"}
            first, second = w[i], w[i + 1]
            writer.consonant(hard.get(first) or _CONSONANTS.get(first, first))
            writer.consonant(hard.get(second) or _CONSONANTS.get(second, second), cluster_with_prev=True)
            i += 2; continue
        if ch == "c":
            soft = (i + 1 < n and w[i + 1] in "eiy") or (i == n - 1 and force_soft_final)
            writer.consonant("स" if soft else "क"); i += 1; continue
        if ch == "g":
            soft = (i + 1 < n and w[i + 1] in "eiy") or (i == n - 1 and force_soft_final)
            writer.consonant("ज" if soft else "ग"); i += 1; continue
        if ch in _CONSONANTS:
            writer.consonant(_CONSONANTS[ch]); i += 1; continue
        i += 1  # unknown character, skip

    return writer.text()


_RE_LATIN_WORD = re.compile(r"[A-Za-z]+")
_RE_ALLCAPS = re.compile(r"^[A-Z]{2,}$")


def translit_text(text: str) -> str:
    """Transliterate every lowercase/mixed-case Latin word in `text`; leaves ALL-CAPS tokens
    alone (those are abbreviations, handled by Task 2's normalize()) and non-Latin text untouched."""
    def repl(m: re.Match) -> str:
        word = m.group(0)
        if _RE_ALLCAPS.match(word):
            return word
        return translit_word(word)
    return _RE_LATIN_WORD.sub(repl, text)


if __name__ == "__main__":
    import sys
    for w in sys.argv[1:]:
        print(w, "->", translit_word(w))
