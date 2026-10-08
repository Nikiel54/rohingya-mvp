import os
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from . import judge as judge_mod  # noqa: E402
from . import transcribe as transcribe_mod  # noqa: E402
from .match import best_match, normalize  # noqa: E402
from .scene import get_turn_context  # noqa: E402
from .schemas import EvaluateResponse, Timings  # noqa: E402

MAX_AUDIO_BYTES = 2 * 1024 * 1024
NO_SPEECH_THRESHOLD = 0.6
AVG_LOGPROB_THRESHOLD = -1.0
FUZZY_PASS_THRESHOLD = 90
FUZZY_CLOSE_THRESHOLD = 75

DEBUG = os.environ.get("DEBUG") == "1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    transcribe_mod.load_model()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "whisperLoaded": transcribe_mod.is_loaded(),
        "geminiEnabled": judge_mod.is_enabled(),
    }


@app.post("/api/evaluate", response_model=EvaluateResponse)
async def evaluate(
    audio: UploadFile,
    turnId: str = Form(...),
    debugTranscript: Optional[str] = Form(None),
):
    context = get_turn_context(turnId)
    if context is None:
        raise HTTPException(status_code=400, detail=f"Unknown turnId: {turnId}")

    if DEBUG and debugTranscript is not None:
        transcript_norm = normalize(debugTranscript)
        unclear_words: list[str] = []
        transcribe_ms = 0
        not_heard = not transcript_norm
    else:
        data = await audio.read()
        if len(data) > MAX_AUDIO_BYTES:
            raise HTTPException(status_code=413, detail="Audio file too large")

        suffix = Path(audio.filename or "").suffix or ".webm"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        try:
            t0 = time.monotonic()
            try:
                result = transcribe_mod.transcribe_audio(tmp_path)
            except Exception:
                result = None
            transcribe_ms = int((time.monotonic() - t0) * 1000)
        finally:
            os.unlink(tmp_path)

        if result is None:
            # Undecodable or corrupt audio (e.g. a truncated recording): treat as not heard
            # rather than failing the request.
            transcript_norm = ""
            unclear_words = []
            not_heard = True
        else:
            transcript_norm = normalize(result["text"])
            unclear_words = [w["word"] for w in result["words"] if w["probability"] < 0.5]

            is_silent = not transcript_norm
            is_no_speech = result["max_no_speech_prob"] > NO_SPEECH_THRESHOLD
            is_low_confidence = result["mean_avg_logprob"] < AVG_LOGPROB_THRESHOLD
            not_heard = is_silent or is_no_speech or is_low_confidence

    if not_heard:
        return EvaluateResponse(
            result="NOT_HEARD",
            transcript=transcript_norm,
            source="speech_check",
            issue="unclear_speech",
            focusWords=[],
            bestReplyId=None,
            tip=None,
            unclearWords=unclear_words,
            timingsMs=Timings(transcribe=transcribe_ms, judge=0),
        )

    score, best_reply = best_match(transcript_norm, context["replies"])
    best_reply_id = best_reply["id"] if best_reply else None

    if score >= FUZZY_PASS_THRESHOLD:
        return EvaluateResponse(
            result="PASS",
            transcript=transcript_norm,
            source="fuzzy",
            issue="none",
            focusWords=[],
            bestReplyId=best_reply_id,
            tip=None,
            unclearWords=unclear_words,
            timingsMs=Timings(transcribe=transcribe_ms, judge=0),
        )

    t_judge0 = time.monotonic()
    gemini_result = await judge_mod.judge(
        line=context["line"],
        intent=context["intent"],
        replies=context["replies"],
        key_words=context["keyWords"],
        transcript=transcript_norm,
        unclear_words=unclear_words,
    )
    judge_ms = int((time.monotonic() - t_judge0) * 1000)

    if gemini_result is not None:
        verdict_map = {"MATCH": "PASS", "PARTIAL": "CLOSE", "MISMATCH": "RETRY"}
        return EvaluateResponse(
            result=verdict_map[gemini_result["verdict"]],
            transcript=transcript_norm,
            source="gemini",
            issue=gemini_result["issue"],
            focusWords=gemini_result["focus_words"],
            bestReplyId=context["replies"][gemini_result["best_reply_index"]]["id"],
            tip=gemini_result["tip"],
            unclearWords=unclear_words,
            timingsMs=Timings(transcribe=transcribe_ms, judge=judge_ms),
        )

    transcript_tokens = set(transcript_norm.split())
    missing_key_words = [kw for kw in context["keyWords"] if kw.lower() not in transcript_tokens]

    if score >= FUZZY_CLOSE_THRESHOLD:
        verdict = "CLOSE"
        issue = "missing_key_word" if missing_key_words else "wrong_meaning"
    else:
        verdict = "RETRY"
        issue = "wrong_meaning"

    return EvaluateResponse(
        result=verdict,
        transcript=transcript_norm,
        source="fallback",
        issue=issue,
        focusWords=missing_key_words,
        bestReplyId=best_reply_id,
        tip=None,
        unclearWords=unclear_words,
        timingsMs=Timings(transcribe=transcribe_ms, judge=judge_ms),
    )
