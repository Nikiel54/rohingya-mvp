from typing import Optional, TypedDict

from faster_whisper import WhisperModel

_model: Optional[WhisperModel] = None


class TranscriptionResult(TypedDict):
    text: str
    words: list[dict]
    max_no_speech_prob: float
    mean_avg_logprob: float


def load_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel("small.en", device="cpu", compute_type="int8")
    return _model


def is_loaded() -> bool:
    return _model is not None


def transcribe_audio(path: str) -> TranscriptionResult:
    model = load_model()
    segments, _info = model.transcribe(
        path,
        language="en",
        beam_size=5,
        word_timestamps=True,
        vad_filter=True,
        condition_on_previous_text=False,
    )
    segments = list(segments)

    text_parts: list[str] = []
    words: list[dict] = []
    no_speech_probs: list[float] = []
    avg_logprobs: list[float] = []

    for seg in segments:
        stripped = seg.text.strip()
        if stripped:
            text_parts.append(stripped)
        no_speech_probs.append(seg.no_speech_prob)
        avg_logprobs.append(seg.avg_logprob)
        if seg.words:
            for w in seg.words:
                words.append({"word": w.word.strip(), "probability": w.probability})

    max_no_speech = max(no_speech_probs) if no_speech_probs else 1.0
    mean_avg_logprob = sum(avg_logprobs) / len(avg_logprobs) if avg_logprobs else -999.0

    return {
        "text": " ".join(text_parts).strip(),
        "words": words,
        "max_no_speech_prob": max_no_speech,
        "mean_avg_logprob": mean_avg_logprob,
    }
