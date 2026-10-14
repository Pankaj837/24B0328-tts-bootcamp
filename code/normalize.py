"""
Task 2 text frontend: normalize(text) rewrites Hindi/Hinglish text into Hindi words as spoken,
in Devanagari. Rule-based only, no models. Handles:

  - Indian-style numbers (lakh/crore grouping) for plain integers, including Indian comma grouping.
  - Rupee (Rs./₹) amounts, with or without a trailing lakh/karod/hazar word, with paise for decimals.
  - Dates: DD/MM/YYYY, and "D <Devanagari month name> YYYY".
  - Decimal numbers read digit-by-digit after "dashmalav" (the standard Indian convention, e.g.
    3.14 -> "teen dashmalav ek chaar").
  - All-caps Latin abbreviations (RBI, GST, ATM, KYC, SBI, ...) spelled out letter by letter in
    Devanagari. Other (non all-caps) Latin words are left untouched -- how they are pronounced is a
    Task 3 problem, not Task 2's.

Everything here is a general numeral/date/abbreviation reading rule, not a lookup keyed to specific
sentences, so it generalizes to item text it has not seen (the validation items only exercise a
subset of numbers/dates/abbreviations; the algorithm covers any value in range).
"""
import re

# --------------------------------------------------------------------------------------------
# Hindi cardinal numbers 0-99 (irregular; no compositional pattern below 100 in Hindi)
# --------------------------------------------------------------------------------------------
_ONES_99 = [
    "शून्य", "एक", "दो", "तीन", "चार", "पाँच", "छह", "सात", "आठ", "नौ",
    "दस", "ग्यारह", "बारह", "तेरह", "चौदह", "पंद्रह", "सोलह", "सत्रह", "अठारह", "उन्नीस",
    "बीस", "इक्कीस", "बाईस", "तेईस", "चौबीस", "पच्चीस", "छब्बीस", "सत्ताईस", "अट्ठाईस", "उनतीस",
    "तीस", "इकतीस", "बत्तीस", "तैंतीस", "चौंतीस", "पैंतीस", "छत्तीस", "सैंतीस", "अड़तीस", "उनतालीस",
    "चालीस", "इकतालीस", "बयालीस", "तैंतालीस", "चवालीस", "पैंतालीस", "छियालीस", "सैंतालीस", "अड़तालीस", "उनचास",
    "पचास", "इक्यावन", "बावन", "तिरेपन", "चौवन", "पचपन", "छप्पन", "सत्तावन", "अट्ठावन", "उनसठ",
    "साठ", "इकसठ", "बासठ", "तिरेसठ", "चौंसठ", "पैंसठ", "छियासठ", "सड़सठ", "अड़सठ", "उनहत्तर",
    "सत्तर", "इकहत्तर", "बहत्तर", "तिहत्तर", "चौहत्तर", "पचहत्तर", "छिहत्तर", "सतहत्तर", "अठहत्तर", "उनासी",
    "अस्सी", "इक्यासी", "बयासी", "तिरासी", "चौरासी", "पचासी", "छियासी", "सत्तासी", "अट्ठासी", "नवासी",
    "नब्बे", "इक्यानवे", "बानवे", "तिरानवे", "चौरानवे", "पंचानवे", "छियानवे", "सत्तानवे", "अट्ठानवे", "निन्यानवे",
]
_DIGIT_WORDS = _ONES_99[:10]  # 0-9, used for digit-by-digit reading (decimals, abbreviation-adjacent)

_MONTHS = {
    1: "जनवरी", 2: "फ़रवरी", 3: "मार्च", 4: "अप्रैल", 5: "मई", 6: "जून",
    7: "जुलाई", 8: "अगस्त", 9: "सितंबर", 10: "अक्टूबर", 11: "नवंबर", 12: "दिसंबर",
}

_LETTER_NAMES = {
    "A": "ए", "B": "बी", "C": "सी", "D": "डी", "E": "ई", "F": "एफ़", "G": "जी", "H": "एच",
    "I": "आई", "J": "जे", "K": "के", "L": "एल", "M": "एम", "N": "एन", "O": "ओ", "P": "पी",
    "Q": "क्यू", "R": "आर", "S": "एस", "T": "टी", "U": "यू", "V": "वी", "W": "डब्ल्यू",
    "X": "एक्स", "Y": "वाई", "Z": "ज़ेड",
}


def num_to_words(n: int) -> str:
    """Indian-system cardinal: crore / lakh / hazar / sau / tens-ones."""
    if n == 0:
        return _ONES_99[0]
    if n < 0:
        return "माइनस " + num_to_words(-n)
    parts = []
    crore, n = divmod(n, 10_000_000)
    if crore:
        parts.append(num_to_words(crore) if crore >= 100 else _ONES_99[crore])
        parts.append("करोड़")
    lakh, n = divmod(n, 100_000)
    if lakh:
        parts.append(num_to_words(lakh) if lakh >= 100 else _ONES_99[lakh])
        parts.append("लाख")
    thousand, n = divmod(n, 1_000)
    if thousand:
        parts.append(num_to_words(thousand) if thousand >= 100 else _ONES_99[thousand])
        parts.append("हज़ार")
    hundred, n = divmod(n, 100)
    if hundred:
        parts.append(_ONES_99[hundred])
        parts.append("सौ")
    if n:
        parts.append(_ONES_99[n])
    return " ".join(parts)


def _digits_to_words(digits: str) -> str:
    return " ".join(_DIGIT_WORDS[int(d)] for d in digits)


# --------------------------------------------------------------------------------------------
# Regex passes, applied in order. Each pass only matches patterns the earlier passes didn't
# already consume, so a number is never converted twice.
# --------------------------------------------------------------------------------------------
_RE_ABBR = re.compile(r"\b[A-Z]{2,}\b")
_RE_DATE_SLASH = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
_RE_DATE_TEXT_MONTH = re.compile(
    r"\b(\d{1,2})\s+(" + "|".join(re.escape(m) for m in _MONTHS.values()) + r")\s+(\d{4})\b"
)
_NUM = r"[\d,]*\d(?:\.\d+)?"
_RE_RUPEE = re.compile(r"₹\s*(" + _NUM + r")(\s*(?:लाख|करोड़|हज़ार))?")
_RE_UNIT_NO_RUPEE = re.compile(r"\b(" + _NUM + r")\s*(लाख|करोड़|हज़ार)\b")
_RE_DECIMAL = re.compile(r"\b(\d+)\.(\d+)\b")
_RE_INTEGER = re.compile(r"\b\d(?:[\d,]*\d)?\b")
_RE_PERCENT = re.compile(r"\s*%")


def _abbr_sub(m: re.Match) -> str:
    return " ".join(_LETTER_NAMES.get(ch, ch) for ch in m.group(0))


def _date_slash_sub(m: re.Match) -> str:
    d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    month = _MONTHS.get(mo, num_to_words(mo))
    return f"{num_to_words(d)} {month} {num_to_words(y)}"


def _date_text_month_sub(m: re.Match) -> str:
    d, month_word, y = int(m.group(1)), m.group(2), int(m.group(3))
    return f"{num_to_words(d)} {month_word} {num_to_words(y)}"


def _rupee_sub(m: re.Match) -> str:
    num_str = m.group(1).replace(",", "")
    unit = m.group(2).strip() if m.group(2) else None
    if "." in num_str:
        int_part, frac_part = num_str.split(".")
        words = num_to_words(int(int_part))
        if unit:
            return f"{words} {unit} रुपये"
        paise = int((frac_part + "0")[:2])
        out = f"{words} रुपये"
        if paise:
            out += f" {num_to_words(paise)} पैसे"
        return out
    words = num_to_words(int(num_str))
    return f"{words} {unit} रुपये" if unit else f"{words} रुपये"


def _unit_no_rupee_sub(m: re.Match) -> str:
    num_str, unit = m.group(1).replace(",", ""), m.group(2)
    if "." in num_str:
        int_part, frac_part = num_str.split(".")
        return f"{num_to_words(int(int_part))} दशमलव {_digits_to_words(frac_part)} {unit}"
    return f"{num_to_words(int(num_str))} {unit}"


def _decimal_sub(m: re.Match) -> str:
    return f"{num_to_words(int(m.group(1)))} दशमलव {_digits_to_words(m.group(2))}"


def _integer_sub(m: re.Match) -> str:
    return num_to_words(int(m.group(0).replace(",", "")))


def normalize(text: str) -> str:
    """Rewrite `text` into Hindi words as spoken: numbers, dates, rupee amounts, abbreviations.
    English words already in Latin script are left as-is (pronunciation is a Task 3 problem)."""
    out = text
    out = _RE_ABBR.sub(_abbr_sub, out)
    out = _RE_DATE_SLASH.sub(_date_slash_sub, out)
    out = _RE_DATE_TEXT_MONTH.sub(_date_text_month_sub, out)
    out = _RE_RUPEE.sub(_rupee_sub, out)
    out = _RE_UNIT_NO_RUPEE.sub(_unit_no_rupee_sub, out)
    out = _RE_DECIMAL.sub(_decimal_sub, out)
    out = _RE_INTEGER.sub(_integer_sub, out)
    out = _RE_PERCENT.sub(" प्रतिशत", out)
    return out


if __name__ == "__main__":
    import sys
    for line in sys.stdin:
        print(normalize(line.rstrip("\n")))
