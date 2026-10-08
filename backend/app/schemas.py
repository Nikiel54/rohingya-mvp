from typing import Literal, Optional

from pydantic import BaseModel

ResultType = Literal["PASS", "CLOSE", "RETRY", "NOT_HEARD"]
SourceType = Literal["speech_check", "fuzzy", "gemini", "fallback"]
IssueType = Literal["none", "missing_key_word", "wrong_meaning", "off_topic", "unclear_speech"]


class Timings(BaseModel):
    transcribe: int
    judge: int


class EvaluateResponse(BaseModel):
    result: ResultType
    transcript: str
    source: SourceType
    issue: IssueType
    focusWords: list[str]
    bestReplyId: Optional[str]
    tip: Optional[str]
    unclearWords: list[str]
    timingsMs: Timings
