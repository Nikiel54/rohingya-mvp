import asyncio
import logging
import os
from typing import Literal, Optional, TypedDict

from google import genai
from google.genai.types import GenerateContentConfig
from pydantic import BaseModel

from .match import normalize

logger = logging.getLogger(__name__)

GEMINI_TIMEOUT_SECONDS = 4.0


class JudgeOutput(BaseModel):
    verdict: Literal["MATCH", "PARTIAL", "MISMATCH"]
    issue: Literal["none", "missing_key_word", "wrong_meaning", "off_topic", "unclear_speech"]
    focus_words: list[str]
    best_reply_index: int
    tip: str


class JudgeResult(TypedDict):
    verdict: Literal["MATCH", "PARTIAL", "MISMATCH"]
    issue: str
    focus_words: list[str]
    best_reply_index: int
    tip: str


_client: Optional[genai.Client] = None
_model_name: Optional[str] = None


def is_enabled() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY"))


def _get_client() -> genai.Client:
    global _client, _model_name
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        _model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
    return _client


PROMPT_TEMPLATE = """You are checking a beginner English learner's spoken reply in a workplace practice app.
The learner is a newcomer to Canada. Judge MEANING, not grammar or accent.
If a supervisor would understand the reply and it fits the intent, it is a MATCH,
even with grammar mistakes ("Yes, I put glove" is a MATCH).

Supervisor said: "{line}"
Intent the reply must meet: {intent}
Example correct replies (numbered from 0):
{numbered_replies}
Key words: {key_words}
Learner's transcribed reply: "{transcript}"
Words the speech recognizer was unsure about: {unclear_words}

Return JSON:
- verdict: MATCH (meets the intent), PARTIAL (right idea but a key word or part is missing
  or unclear), MISMATCH (wrong meaning, off topic, or not an answer).
- issue: the main problem, or "none" for a MATCH.
- focus_words: up to 3 words from the example replies the learner should practice.
  Only words that appear in the example replies.
- best_reply_index: the example reply closest to what the learner tried to say.
- tip: one short sentence in very simple English, under 15 words.
"""


def build_prompt(line: str, intent: str, replies: list[dict], key_words: list[str], transcript: str, unclear_words: list[str]) -> str:
    numbered_replies = "\n".join(f"{i}. {r['text']}" for i, r in enumerate(replies))
    return PROMPT_TEMPLATE.format(
        line=line,
        intent=intent,
        numbered_replies=numbered_replies,
        key_words=", ".join(key_words) if key_words else "(none)",
        transcript=transcript,
        unclear_words=", ".join(unclear_words) if unclear_words else "(none)",
    )


def _call_gemini_sync(prompt: str) -> JudgeOutput:
    client = _get_client()
    response = client.models.generate_content(
        model=_model_name,
        contents=prompt,
        config=GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json",
            response_schema=JudgeOutput,
        ),
    )
    return JudgeOutput.model_validate_json(response.text)


async def judge(
    line: str,
    intent: str,
    replies: list[dict],
    key_words: list[str],
    transcript: str,
    unclear_words: list[str],
) -> Optional[JudgeResult]:
    """Returns None (caller should fall back) on any error, timeout, or when disabled."""
    if not is_enabled():
        return None

    prompt = build_prompt(line, intent, replies, key_words, transcript, unclear_words)

    try:
        output = await asyncio.wait_for(
            asyncio.to_thread(_call_gemini_sync, prompt),
            timeout=GEMINI_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.warning("Gemini judge timed out after %.1fs", GEMINI_TIMEOUT_SECONDS)
        return None
    except Exception as e:
        logger.warning("Gemini judge failed: %s", e)
        return None

    allowed_words: set[str] = set()
    for r in replies:
        allowed_words.update(normalize(r["text"]).split())
    focus_words = [w for w in output.focus_words if normalize(w) in allowed_words][:3]

    best_reply_index = output.best_reply_index
    if not (0 <= best_reply_index < len(replies)):
        best_reply_index = 0

    return {
        "verdict": output.verdict,
        "issue": output.issue,
        "focus_words": focus_words,
        "best_reply_index": best_reply_index,
        "tip": output.tip[:120],
    }
