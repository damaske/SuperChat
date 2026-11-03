import re


SUPPORTED_LANGUAGES = {"az", "ru", "en"}

_AZERBAIJANI_WORDS = {
    "axtar", "tap", "uçuş", "uçuşları", "filmlər", "göstərilir",
    "göstərin", "hansı", "ucuz", "ucuzdan", "simsiz", "qulaqlıqlar",
    "dollardan", "sabah", "bu", "gün", "üçün", "seans", "kinoteatr",
    "harada", "var", "mənə", "göstər", "əlavə", "çıxar",
}
_RUSSIAN_WORDS = {
    "найди", "найти", "рейс", "рейсы", "из", "в", "какие", "фильмы",
    "идут", "покажи", "дешевле", "товар", "товары", "наушники",
    "беспроводные", "завтра", "сегодня", "сеанс", "кинотеатр",
    "места", "наличии", "сравни", "самый", "дешёвый",
}
_ENGLISH_WORDS = {
    "find", "search", "flight", "flights", "from", "to", "what", "which",
    "movies", "movie", "showing", "show", "headphones", "wireless",
    "under", "cheaper", "tomorrow", "today", "seats", "available",
    "compare", "details", "product", "products", "cart",
}


def detect_language(message: str) -> str | None:
    """Return a confident language or None when context should be retained."""
    if not message or not message.strip():
        return None

    text = message.lower()
    words = set(re.findall(r"[a-zа-яёəıöüğşç]+", text))
    tokens = words
    scores = {
        "az": len(words & _AZERBAIJANI_WORDS),
        "ru": len(words & _RUSSIAN_WORDS),
        "en": len(words & _ENGLISH_WORDS),
    }

    if re.search(r"[əıöüğşç]", text):
        scores["az"] += 2
    has_azerbaijani_suffix = bool(
        re.search(
            r"(?:^|[-\s])(da|də|dan|dən|dır|dir|lər|lar)(?:$|[\s?.!,])",
            text,
        )
    )
    if has_azerbaijani_suffix:
        scores["az"] += 4
    if re.search(r"[а-яё]", text):
        scores["ru"] += 2

    best = max(scores, key=scores.get)
    best_score = scores[best]
    if best_score == 0:
        return None

    # Short follow-ups such as "Tomorrow?" or a proper noun should not
    # unexpectedly switch the conversation language.
    if len(tokens) <= 2 and not re.search(r"[əıöüğşçа-яё]", text):
        return None

    tied = [language for language, score in scores.items() if score == best_score]
    if len(tied) > 1:
        return None
    return best
