"""
masking.py - hide personal data from the AI (input masking) and check what
the AI sends back (output masking).

    User:     "My email is asha@gmail.com, phone 9876543210"
    AI sees:  "My email is [EMAIL_1], phone [PHONE_1]"
    AI says:  "Thanks! We'll contact you at [EMAIL_1]."
    User sees: "Thanks! We'll contact you at asha@gmail.com."

The real values never leave our server. We keep a small lookup table
(placeholder -> real value) for ONE request, and use it to:
  - put real values back into tool arguments before a tool runs
    (the tool runs on our server, so it may see them)
  - put real values back into the final reply, so the user sees their own data
  - redact anything sensitive the AI wrote that did NOT come from the user
    (output masking: the AI should never "invent" a phone number or card)

Run `python check_masking.py` to test all of this.
"""
import re

# Order matters: more specific patterns first, so a card number is not partly
# matched as a phone number. Separators inside a number must be consistent
# (\1), so dates like "2026-10-12 2026-10-20" are never mistaken for a card.
PATTERNS: list[tuple[str, re.Pattern]] = [
    ("API_KEY", re.compile(r"\b(?:gsk|sk|pk|rk)[-_][A-Za-z0-9_-]{16,}\b")),
    ("EMAIL",   re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}\b")),
    ("CARD",    re.compile(r"(?<![\d-])(?:\d{4}([ -]?)\d{4}\1\d{4}\1\d{1,4}"     # Visa / MC / RuPay
                           r"|3[47]\d{2}([ -]?)\d{6}\2\d{5})(?![\d-])")),         # Amex
    ("AADHAAR", re.compile(r"(?<![\d-])[2-9]\d{3}([ -]?)\d{4}\1\d{4}(?![\d-])")),
    ("PHONE",   re.compile(r"(?<![\w+-])(?:\+91[ -]?|0)?[6-9]\d{2}"
                           r"(?:\d{2}[ -]?\d{5}|[ -]\d{3}[ -]\d{4})(?![\d-])")),   # 98765 43210 / 987-654-3210
    ("PAN",     re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")),
    ("UPI",     re.compile(r"\b[A-Za-z0-9._-]{2,}@[A-Za-z]{3,}\b")),   # e.g. asha@okaxis
]
KINDS = [kind for kind, _ in PATTERNS]

# How redacted data is shown to the user, e.g. "[phone number hidden]".
LABELS = {"API_KEY": "key", "EMAIL": "email", "CARD": "card number", "AADHAAR": "Aadhaar number",
          "PHONE": "phone number", "PAN": "PAN", "UPI": "UPI ID"}

# Models sometimes copy a placeholder slightly wrong. All of these mean [EMAIL_1]:
#   [EMAIL_1]  [Email_1]  [EMAIL 1]  [EMAIL-1]  [EMAIL1]  <EMAIL_1>  {EMAIL_1}
#   \[EMAIL\_1\] (markdown-escaped)  EMAIL_1 (no brackets)
# Without brackets we only accept the exact UPPERCASE_N form, so normal words
# like "phone 1" or "card 2" in a sentence are never touched.
_KIND = r"(?P<kind>" + "|".join(k.replace("_", r"[\s_\\-]*") for k in KINDS) + r")"
_NUM = r"[\s_\\-]*(?P<num>\d{1,3})"
LOOSE_PLACEHOLDER = re.compile(
    r"\\?[\[<{]\s*" + _KIND + _NUM + r"\s*\\?[\]>}]"                    # with brackets, any case
    r"|(?<![\w\[<{(])(?P<kind2>" + "|".join(k.replace("_", r"\\?_") for k in KINDS)
    + r")\\?_(?P<num2>\d{1,3})(?![\w\]>})])",                           # no brackets, exact
    re.IGNORECASE,
)
EXACT_PLACEHOLDER = re.compile(r"\[(?:" + "|".join(KINDS) + r")_\d+\]")

UNKNOWN_PLACEHOLDER_TEXT = "(hidden)"


def _luhn_ok(number: str) -> bool:
    """Real card numbers pass the Luhn checksum. Random long numbers usually don't."""
    digits = [int(d) for d in re.sub(r"\D", "", number)]
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def _is_real_match(kind: str, value: str) -> bool:
    if kind == "CARD":
        return _luhn_ok(value)
    return True


def _normalise_kind(text: str) -> str:
    """'Api Key' / 'api_key' / 'APIKEY' -> 'API_KEY'."""
    letters = re.sub(r"[^A-Z]", "", text.upper())
    for kind in KINDS:
        if kind.replace("_", "") == letters:
            return kind
    return letters


class Masker:
    """Create one per request. Same value -> same placeholder within a request."""

    def __init__(self) -> None:
        self.to_real: dict[str, str] = {}          # "[EMAIL_1]" -> "asha@gmail.com"
        self._to_placeholder: dict[str, str] = {}  # "asha@gmail.com" -> "[EMAIL_1]"
        self._counts: dict[str, int] = {}

    # ---- input masking: real -> placeholder -----------------------------
    def mask(self, text: str) -> str:
        if not text:
            return text
        for kind, pattern in PATTERNS:
            text = pattern.sub(lambda m, k=kind: self._placeholder_for(k, m.group(0)), text)
        return text

    def _placeholder_for(self, kind: str, value: str) -> str:
        if not _is_real_match(kind, value):
            return value
        if value not in self._to_placeholder:
            self._counts[kind] = self._counts.get(kind, 0) + 1
            placeholder = f"[{kind}_{self._counts[kind]}]"
            self._to_placeholder[value] = placeholder
            self.to_real[placeholder] = value
        return self._to_placeholder[value]

    # ---- unmasking: placeholder -> real ---------------------------------
    def unmask(self, text: str, unknown: str | None = None) -> str:
        """Swap placeholders (even slightly mangled ones) back to real values.

        unknown: what to write for a placeholder we never created (the model
        made it up). None = leave it as it is.
        """
        if not text:
            return text

        def swap(m: re.Match) -> str:
            kind = _normalise_kind(m.group("kind") or m.group("kind2"))
            num = int(m.group("num") or m.group("num2"))
            real = self.to_real.get(f"[{kind}_{num}]")
            if real is not None:
                return real
            return m.group(0) if unknown is None else unknown

        return LOOSE_PLACEHOLDER.sub(swap, text)

    def unmask_value(self, value):
        """Unmask strings inside tool arguments (dicts / lists / strings)."""
        if isinstance(value, str):
            return self.unmask(value)
        if isinstance(value, dict):
            return {k: self.unmask_value(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.unmask_value(v) for v in value]
        return value

    # ---- output masking: check what the AI wrote ------------------------
    def clean_reply(self, text: str) -> str:
        """Make the model's final answer safe and readable for the user:
        1. redact sensitive data the model produced by itself
        2. put the user's own values back where the model used placeholders
        3. replace any placeholder the model invented with "(hidden)"
        """
        if not text:
            return text
        for kind, pattern in PATTERNS:
            text = pattern.sub(
                lambda m, k=kind: f"[{LABELS[k]} hidden]" if _is_real_match(k, m.group(0)) else m.group(0),
                text,
            )
        return self.unmask(text, unknown=UNKNOWN_PLACEHOLDER_TEXT)
