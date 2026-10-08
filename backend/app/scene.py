import json
from functools import lru_cache
from pathlib import Path
from typing import Optional, TypedDict

SCENE_PATH = Path(__file__).resolve().parent.parent.parent / "frontend" / "public" / "scene" / "scene.json"


class TurnContext(TypedDict):
    line: str
    intent: str
    keyWords: list[str]
    replies: list[dict]


@lru_cache
def load_scene() -> dict:
    return json.loads(SCENE_PATH.read_text(encoding="utf-8"))


def get_turn_context(turn_id: str) -> Optional[TurnContext]:
    scene = load_scene()

    if turn_id == "repeat_request":
        rr = scene["repeatRequest"]
        replies = [{"id": f"repeat_request_{i}", "text": text} for i, text in enumerate(rr["accepted"])]
        return {
            "line": rr["text"],
            "intent": "The learner politely asks the supervisor to repeat what they said.",
            "keyWords": [],
            "replies": replies,
        }

    for turn in scene["turns"]:
        if turn["id"] == turn_id:
            return {
                "line": turn["line"]["text"],
                "intent": turn["say"]["intent"],
                "keyWords": turn["say"]["keyWords"],
                "replies": turn["say"]["replies"],
            }

    return None
