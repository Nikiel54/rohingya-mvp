# First Shift demo
Build spec: SPEC.md. Build one phase at a time and stop when its "Done when" passes.

Rules:
- Learners always SPEAK ENGLISH. Rohingya is only placeholder help audio. Never generate or translate Rohingya.
- No database, no accounts, no hosted services except the optional Gemini call.
- Gemini receives transcript TEXT only. Never send audio to it.
- Never pass the expected answer to Whisper as a prompt.
- Keep the scene data-driven: no turn content hard-coded in components.
- Run: backend `uvicorn app.main:app --reload --port 8000`, frontend `npm run dev`.
