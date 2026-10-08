import re

from rapidfuzz import fuzz

CONTRACTIONS = {
    "i'll": "i will",
    "you'll": "you will",
    "we'll": "we will",
    "they'll": "they will",
    "don't": "do not",
    "doesn't": "does not",
    "didn't": "did not",
    "can't": "can not",
    "won't": "will not",
    "isn't": "is not",
    "aren't": "are not",
    "wasn't": "was not",
    "weren't": "were not",
    "what's": "what is",
    "that's": "that is",
    "it's": "it is",
    "i'm": "i am",
    "you're": "you are",
    "we're": "we are",
    "they're": "they are",
    "i've": "i have",
    "you've": "you have",
    "we've": "we have",
    "they've": "they have",
    "let's": "let us",
    "there's": "there is",
    "he's": "he is",
    "she's": "she is",
}

DIGIT_WORDS = {
    "1": "one",
    "2": "two",
    "3": "three",
    "4": "four",
    "5": "five",
    "6": "six",
    "7": "seven",
    "8": "eight",
    "9": "nine",
    "10": "ten",
    "11": "eleven",
    "12": "twelve",
}

_OCLOCK_PLACEHOLDER = "oclockplaceholder"


def normalize(text: str) -> str:
    text = text.lower().strip()
    text = text.replace("o'clock", _OCLOCK_PLACEHOLDER)

    for contraction, expansion in CONTRACTIONS.items():
        text = re.sub(rf"\b{re.escape(contraction)}\b", expansion, text)

    text = text.replace(_OCLOCK_PLACEHOLDER, "oclock")
    text = re.sub(r"[^\w\s]", " ", text)

    tokens = text.split()
    tokens = [DIGIT_WORDS.get(tok, tok) for tok in tokens]
    return " ".join(tokens)


def best_match(transcript_norm: str, replies: list[dict]) -> tuple[float, dict | None]:
    best_score = -1.0
    best_reply: dict | None = None
    for reply in replies:
        score = fuzz.ratio(transcript_norm, normalize(reply["text"]))
        if score > best_score:
            best_score = score
            best_reply = reply
    return best_score, best_reply
