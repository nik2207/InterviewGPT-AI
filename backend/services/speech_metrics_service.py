import re
from typing import Literal

from core.config.settings import settings

InputMode = Literal["typed", "speech", "mixed"]

SPEECH_METRICS_DISCLAIMER = (
    "Descriptive timing and word-use metrics only. "
    "Not a measure of confidence, personality, or psychological state."
)

DEFAULT_FILLER_WORDS = (
    "um",
    "uh",
    "like",
    "actually",
    "basically",
    "literally",
    "sort of",
    "kind of",
    "you know",
)


def count_words(text: str) -> int:
    """Count words as sequences of letters/apostrophes bounded by word boundaries."""
    cleaned = (text or "").strip()
    if not cleaned:
        return 0
    return len(re.findall(r"\b[\w']+\b", cleaned, flags=re.UNICODE))


def _filler_patterns() -> list[tuple[str, re.Pattern[str]]]:
    fillers = settings.speech_filler_word_list or DEFAULT_FILLER_WORDS
    patterns: list[tuple[str, re.Pattern[str]]] = []
    for phrase in fillers:
        phrase = phrase.strip().lower()
        if not phrase:
            continue
        if " " in phrase:
            patterns.append(
                (phrase, re.compile(rf"(?<!\w){re.escape(phrase)}(?!\w)", re.IGNORECASE))
            )
        else:
            patterns.append(
                (phrase, re.compile(rf"\b{re.escape(phrase)}\b", re.IGNORECASE))
            )
    return patterns


def count_filler_words(text: str) -> tuple[int, list[str]]:
    cleaned = (text or "").strip()
    if not cleaned:
        return 0, []
    detected: list[str] = []
    total = 0
    for label, pattern in _filler_patterns():
        matches = pattern.findall(cleaned)
        if matches:
            total += len(matches)
            if label not in detected:
                detected.append(label)
    return total, detected


def compute_words_per_minute(word_count: int, duration_seconds: float | None) -> float | None:
    if duration_seconds is None or duration_seconds < 1.0 or word_count <= 0:
        return None
    return round(word_count / (duration_seconds / 60.0), 1)


def build_speech_metrics(
    *,
    answer_text: str,
    input_mode: InputMode,
    duration_seconds: float | None = None,
) -> dict:
    word_count = count_words(answer_text)
    filler_count, filler_used = count_filler_words(answer_text)

    metrics: dict = {
        "input_mode": input_mode,
        "word_count": word_count,
        "filler_word_count": filler_count,
        "filler_words_used": filler_used,
        "disclaimer": SPEECH_METRICS_DISCLAIMER,
    }

    if input_mode == "typed":
        metrics["duration_seconds"] = None
        metrics["words_per_minute"] = None
        metrics["speech_timing_available"] = False
        return metrics

    if duration_seconds is not None and duration_seconds >= 1.0:
        metrics["duration_seconds"] = round(duration_seconds, 1)
        metrics["words_per_minute"] = compute_words_per_minute(word_count, duration_seconds)
        metrics["speech_timing_available"] = metrics["words_per_minute"] is not None
    else:
        metrics["duration_seconds"] = None
        metrics["words_per_minute"] = None
        metrics["speech_timing_available"] = False

    return metrics
