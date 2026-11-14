from services.speech_metrics_service import (
    build_speech_metrics,
    compute_words_per_minute,
    count_filler_words,
    count_words,
)


def test_count_words_basic():
    assert count_words("Hello world from Python") == 4


def test_count_words_empty():
    assert count_words("   ") == 0


def test_filler_word_counting():
    count, used = count_filler_words("Um, I think like, you know, basically yes.")
    assert count >= 3
    assert "um" in used or "like" in used


def test_wpm_unavailable_without_duration():
    assert compute_words_per_minute(100, None) is None
    assert compute_words_per_minute(100, 0.5) is None


def test_wpm_with_valid_duration():
    assert compute_words_per_minute(120, 60) == 120.0


def test_typed_metrics_no_timing():
    metrics = build_speech_metrics(
        answer_text="A solid typed answer with enough words.",
        input_mode="typed",
        duration_seconds=None,
    )
    assert metrics["speech_timing_available"] is False
    assert metrics["words_per_minute"] is None
    assert metrics["word_count"] > 0


def test_speech_metrics_with_duration():
    metrics = build_speech_metrics(
        answer_text="word " * 50,
        input_mode="speech",
        duration_seconds=60.0,
    )
    assert metrics["speech_timing_available"] is True
    assert metrics["words_per_minute"] == 50.0
