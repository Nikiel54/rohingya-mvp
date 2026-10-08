# First Shift Demo: Build Spec

Oct 7, 2026 · @Nikiel

## Overview

First Shift is a single-page demo where a learner practices spoken English through one workplace scene: a supervisor walks them through their first day at work. It is a working demo for the WAT.ai team, not a product, and should take about 10 to 15 hours to build with Claude Code.

Each turn of the scene runs the same three-step loop:

1. **Hear.** The supervisor's English line plays ("Please put on your gloves"). The learner can replay it at slow speed.
2. **Point.** The learner taps the one picture of three that matches the meaning. No speech recognition is involved, so this step always works.
3. **Say.** The learner hears a model English reply, then holds the mic button and answers **in English**. The backend transcribes the answer, checks it against the turn's intent, and returns feedback on what was missed.

A "Can you repeat that, please?" button is on screen throughout the hear and point steps. The learner must *say* that phrase in English to use it, and the supervisor then repeats the line slowly.

Rohingya appears only as optional help audio explaining what to do. In this demo it is placeholder audio, clearly labeled, until community members record the real clips. Never machine-translate or synthesize Rohingya.

**In scope:** one scene of 6 turns, the hear/point/say loop, the spoken repeat request, feedback (color, icon, sound, highlighted words), an end-of-scene recap, and a phone demo over an HTTPS tunnel.

**Out of scope:** accounts, a database, multiple scenes, free-form AI conversation, phoneme-level pronunciation scoring, saved progress, and production deployment.

## Tech stack and project layout

Everything is open source and runs on your laptop. The only key is a free-tier Gemini key from Google AI Studio, and the app still works without it.

| Layer | Choice | Notes |
| --- | --- | --- |
| Frontend | React + Vite + TypeScript | One page, no router. Plain CSS or Tailwind. |
| Backend | Python 3.11+, FastAPI, Uvicorn | One endpoint, `POST /api/evaluate`, plus `GET /api/health` |
| Speech-to-text | faster-whisper, model `small.en`, CPU, `int8` | Loaded once at startup. Audio never leaves the laptop. |
| Fuzzy matching | rapidfuzz | Fast path before any LLM call |
| Intent judge | Gemini Flash-Lite via the `google-genai` SDK | Text only, structured JSON output, optional |
| English audio | Piper TTS, run once by a script | Static MP3s at normal and slow speed |
| Pictures | Book pictograms (with permission) or ARASAAC | Static PNG/SVG files |
| Scene data | `scene.json` | No database |
| Phone demo | Cloudflare quick tunnel (`cloudflared`) | Free HTTPS link, no account |

```
first-shift/
├── CLAUDE.md                # Points Claude Code at this spec + rules below
├── frontend/
│   ├── vite.config.ts       # Proxies /api to localhost:8000
│   ├── public/scene/
│   │   ├── scene.json
│   │   ├── audio/           # Generated MP3s + placeholder Rohingya clips
│   │   ├── images/          # One picture per option
│   │   └── sfx/             # correct.mp3, retry.mp3
│   └── src/
│       ├── App.tsx          # Scene state machine
│       ├── types.ts         # Scene types, mirrors scene.json
│       ├── api.ts           # evaluate() call
│       ├── audio.ts         # playback + recording helpers
│       └── components/      # Screen pieces (see Phase 5)
├── backend/
│   ├── requirements.txt
│   ├── .env.example         # GEMINI_API_KEY=
│   └── app/
│       ├── main.py          # FastAPI app, startup model load, routes
│       ├── scene.py         # Loads scene.json, looks up turns
│       ├── transcribe.py    # faster-whisper wrapper
│       ├── match.py         # Normalize + rapidfuzz scoring
│       ├── judge.py         # Gemini intent judge + fallback
│       └── schemas.py       # Pydantic request/response models
└── scripts/
    └── generate_audio.py    # Piper: every English line at 2 speeds
```

The backend reads the same `frontend/public/scene/scene.json` file the frontend loads, so the scene has one source of truth.

## Scene data format

The whole scene lives in `scene.json`. Every spoken line has an `id`, and its audio paths follow one convention, so the JSON holds no file paths for audio:

- English line → `audio/<id>.mp3` and `audio/<id>_slow.mp3` (made by the Phase 2 script)
- Rohingya help for a turn → `audio/help_<turnId>.mp3` (placeholder until recorded)
- Picture option → `images/<optionId>.svg` (switch the extension in one constant when real PNG pictograms arrive)

One turn, written out in full:

```json
{
  "id": "first-shift",
  "title": "First Shift",
  "repeatRequest": {
    "id": "repeat_request",
    "text": "Can you repeat that, please?",
    "accepted": [
      "can you repeat that please",
      "can you say that again",
      "repeat please",
      "sorry can you repeat that"
    ]
  },
  "turns": [
    {
      "id": "t2",
      "line": { "id": "t2_line", "text": "Please put on your gloves." },
      "point": {
        "options": [
          { "id": "gloves", "label": "gloves" },
          { "id": "hat", "label": "hat" },
          { "id": "boots", "label": "boots" }
        ],
        "correct": "gloves"
      },
      "say": {
        "intent": "The learner agrees to put on the gloves.",
        "keyWords": ["gloves"],
        "replies": [
          { "id": "t2_r0", "text": "Okay, I will put on my gloves." },
          { "id": "t2_r1", "text": "Okay." },
          { "id": "t2_r2", "text": "Yes, I will put them on." }
        ]
      }
    }
  ]
}
```

Rules for the data:

- `replies[0]` is the **model reply**, played before the learner speaks. All replies count as correct.
- `keyWords` are the words highlighted in feedback when missing. A short reply like "Okay." can still pass without them.
- The frontend shuffles the picture options on each turn so the correct one is not always first.

The full scene, six turns in a warehouse:

| Turn | Supervisor says | Pictures (correct first) | Model reply | Other accepted replies | Intent |
| --- | --- | --- | --- | --- | --- |
| t1 | Good morning! Welcome to your first day. | wave\_hello, sleeping, eating | Good morning. Thank you. | Hello. / Good morning. / Thank you. | Greets the supervisor back |
| t2 | Please put on your gloves. | gloves, hat, boots | Okay, I will put on my gloves. | Okay. / Yes, I will put them on. | Agrees to put on gloves |
| t3 | Put the boxes on the shelf. | boxes\_shelf, boxes\_floor, boxes\_truck | Okay, I will put the boxes on the shelf. | Okay. / Yes, on the shelf. | Agrees to put boxes on the shelf |
| t4 | Your break is at twelve o'clock. | clock\_12, clock\_3, clock\_8 | Okay. My break is at twelve. | Okay. / Twelve o'clock, thank you. | Acknowledges the break time |
| t5 | Wash your hands before you eat. | wash\_hands, shower, laundry | Okay, I will wash my hands. | Okay. / Yes, I will. | Agrees to wash hands before eating |
| t6 | Do you have any questions? | raise\_hand, sleeping, eating | Yes. Where is the bathroom? | No, thank you. / Where is the bathroom? | Answers whether they have a question; asking one is a pass |

Turn t6 deliberately has two very different correct answers. It shows why the intent judge exists: fuzzy matching alone can't tell that "No, I don't have any questions" is also a fine reply.

## Phase 1: Scaffolding (about 1 hour)

Goal: both apps start, and the frontend can reach the backend through the Vite proxy.

1. Create the folder layout from the previous section.
2. Frontend: `npm create vite@latest frontend -- --template react-ts`. In `vite.config.ts`, proxy `/api` to `http://localhost:8000` and set `server.host: true` so the tunnel can reach it later.
3. Backend: a virtual environment and `requirements.txt` with `fastapi`, `uvicorn[standard]`, `python-multipart`, `faster-whisper`, `rapidfuzz`, `google-genai`, `python-dotenv`, `pydantic`.
4. `app/main.py` exposes `GET /api/health` returning `{"ok": true, "whisperLoaded": false, "geminiEnabled": false}`. The flags get real values in Phases 3 and 4.
5. Copy the full six-turn `scene.json` from the previous section into `frontend/public/scene/`. Add `src/types.ts` with TypeScript types that mirror it.
6. Write `CLAUDE.md` at the repo root:

```markdown
# First Shift demo
Build spec: SPEC.md. Build one phase at a time and stop when its "Done when" passes.

Rules:
- Learners always SPEAK ENGLISH. Rohingya is only placeholder help audio. Never generate or translate Rohingya.
- No database, no accounts, no hosted services except the optional Gemini call.
- Gemini receives transcript TEXT only. Never send audio to it.
- Never pass the expected answer to Whisper as a prompt.
- Keep the scene data-driven: no turn content hard-coded in components.
- Run: backend `uvicorn app.main:app --reload --port 8000`, frontend `npm run dev`.
```

Save this spec as `SPEC.md` in the repo root (export the doc as Markdown) so Claude Code can read it.

**Done when:** `npm run dev` shows a placeholder page, and fetching `/api/health` from the page returns the JSON above.

## Phase 2: English audio generation (about 1 to 2 hours)

Goal: every English line in `scene.json` exists as an MP3 at normal and slow speed, generated once and served as static files.

1. Install Piper (`pip install piper-tts`) and download one English voice, for example `en_US-lessac-medium`. Piper's command-line flags have changed between versions, so have Claude Code check the installed version's README before writing the call.
2. Install ffmpeg for WAV-to-MP3 conversion (`winget install ffmpeg` on Windows, `brew install ffmpeg` on Mac).
3. `scripts/generate_audio.py` reads `scene.json` and collects every line with an `id`: each turn's `line`, every reply, and `repeatRequest`.
4. For each line it writes `audio/<id>.mp3` at normal speed and `audio/<id>_slow.mp3` with Piper's length scale set to about 1.4 (higher is slower).
5. For each turn it writes a **placeholder** help clip `audio/help_<turnId>.mp3`: an English voice saying "Placeholder. Rohingya help for turn \<n> goes here." The word "Placeholder" must be audible so nobody mistakes it for real content.
6. It writes two short sound effects with Python's built-in `wave` module (no extra libraries): `sfx/correct.mp3` (a rising two-note chime) and `sfx/retry.mp3` (a soft low tone).
7. It skips files that already exist unless run with `--force`, and prints a summary of what it made.

Pictures are not generated. Put one image per option ID in `public/scene/images/`. Until the real pictograms are ready, Claude Code can make simple placeholder SVGs with the option label written on them.

**Done when:** running the script twice produces every file the scene references, the second run makes nothing new, and each MP3 plays in a browser.

## Phase 3: Evaluate endpoint, transcription and matching (about 2 to 3 hours)

Goal: `POST /api/evaluate` takes a recording and a turn ID and returns a verdict, using only local tools. Gemini is added in Phase 4.

&#91;embedded content: evaluation pipeline · 3 checks, 4 outcomes\]

Every attempt goes through the local speech check and fuzzy match first. Gemini only sees transcripts that are neither silent nor a near-exact match.

### Request and response

Request: `multipart/form-data` with `audio` (the recording file) and `turnId` (a turn ID such as `t2`, or `repeat_request`). The backend treats `repeat_request` as a pseudo-turn: intent "The learner politely asks the supervisor to repeat what they said," replies = `repeatRequest.accepted`.

Response (`schemas.py`):

```json
{
  "result": "PASS | CLOSE | RETRY | NOT_HEARD",
  "transcript": "okay i will put on my gloves",
  "source": "speech_check | fuzzy | gemini | fallback",
  "issue": "none | missing_key_word | wrong_meaning | off_topic | unclear_speech",
  "focusWords": ["gloves"],
  "bestReplyId": "t2_r0",
  "tip": null,
  "unclearWords": [],
  "timingsMs": { "transcribe": 900, "judge": 0 }
}
```

Return 400 for an unknown `turnId` and 413 for audio over 2 MB.

### Transcription (`transcribe.py`)

- Load `WhisperModel("small.en", device="cpu", compute_type="int8")` **once**, in FastAPI's lifespan handler, and set `whisperLoaded` in the health check.
- Save the upload to a temp file that keeps its extension (Chrome sends WebM, iPhone Safari sends MP4). faster-whisper decodes both itself, with no ffmpeg needed.
- Call `transcribe(path, language="en", beam_size=5, word_timestamps=True, vad_filter=True, condition_on_previous_text=False)`.
- **Do not pass `initial_prompt`** or any expected answer. It biases Whisper toward the right answer and hides mistakes.
- Return the joined text, each word with its probability, the highest segment `no_speech_prob`, and the mean `avg_logprob`.

### Speech check (before any matching)

Return `NOT_HEARD` with `source: "speech_check"` when the normalized transcript is empty, every segment's `no_speech_prob` is above 0.6, or the mean `avg_logprob` is below -1.0. This also catches most cases where the learner spoke Rohingya, since the English-only model produces low-confidence nonsense. Treat both thresholds as starting values to tune in Phase 6. Words with probability below 0.5 go into `unclearWords`.

### Matching (`match.py`)

Normalize both the transcript and each reply the same way:

1. Lowercase and strip punctuation.
2. Expand common contractions (`i'll` → `i will`, `don't` → `do not`, `what's` → `what is`). Keep `o'clock` as one word.
3. Turn digits 1 to 12 into words. Whisper writes "12" where the reply says "twelve", which would otherwise fail turn t4.

Score with `rapidfuzz.fuzz.ratio` against every reply and keep the best score and its reply ID. Use `ratio`, not `token_set_ratio`: the set version scores "okay I will put on my hat" as a perfect match for "Okay."

- Best score 90 or higher → `PASS`, `source: "fuzzy"`, no LLM call.
- Otherwise → the intent judge (Phase 4). Until Phase 4 exists, and whenever Gemini is unavailable: 75 to 89 → `CLOSE`, below 75 → `RETRY`, with `source: "fallback"`.
- For anything but `PASS`, `focusWords` = the turn's `keyWords` missing from the transcript, and `bestReplyId` = the closest reply.

**Done when:** posting the generated file `audio/t2_r0.mp3` with `turnId=t2` returns `PASS`, the same file with `turnId=t3` does not, a silent recording returns `NOT_HEARD`, and a second request is fast because the model is already loaded. A small `scripts/try_evaluate.py` that posts a file and prints the response makes this quick to check.

## Phase 4: Gemini intent judge (about 2 to 3 hours)

Goal: attempts that miss the fuzzy fast path get judged on **meaning**, with feedback that points at what was missed. The app must keep working when Gemini is missing, slow or rate-limited.

### Setup

- `.env`: `GEMINI_API_KEY=` and `GEMINI_MODEL=gemini-2.5-flash-lite`. Check the current free-tier model names in Google AI Studio and update the default if it has changed.
- No key → `geminiEnabled: false` in the health check, and every non-fast-path attempt uses the Phase 3 fallback.
- Send **text only**: the supervisor line, the intent, the replies, the transcript and the unclear words. Never send audio or anything identifying. Free-tier inputs may be used by Google and read by reviewers.

### Call

Use `google-genai`: `client.models.generate_content(model, contents=prompt, config=GenerateContentConfig(temperature=0, response_mime_type="application/json", response_schema=JudgeOutput))`, where `JudgeOutput` is a Pydantic model:

```python
class JudgeOutput(BaseModel):
    verdict: Literal["MATCH", "PARTIAL", "MISMATCH"]
    issue: Literal["none", "missing_key_word", "wrong_meaning", "off_topic", "unclear_speech"]
    focus_words: list[str]
    best_reply_index: int
    tip: str
```

Run the call with a 4-second timeout (`asyncio.wait_for` around `asyncio.to_thread`). On a timeout, a 429, any other error, or unparseable output, fall back to the Phase 3 thresholds with `source: "fallback"`, and log the reason.

### Prompt (`judge.py`)

```text
You are checking a beginner English learner's spoken reply in a workplace practice app.
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
```

### Validate the output before using it

- `best_reply_index` out of range → use 0.
- Drop any `focus_words` that don't appear in the turn's replies. The model must not invent content.
- Cut `tip` to 120 characters.

Map the verdict: `MATCH` → `PASS`, `PARTIAL` → `CLOSE`, `MISMATCH` → `RETRY`. Set `source: "gemini"` and record the judge time in `timingsMs`.

**Done when:** for turn t6, "No, I don't have any questions" returns `PASS` from Gemini, "Yes, I will put on my gloves" returns `RETRY`, and the same requests with the key removed still return a fallback verdict instead of an error. Test with typed transcripts (add an optional debugTranscript form field to the endpoint that skips Whisper, honored only when DEBUG=1) through a small `--text` option on the try script, so you don't have to record each case.

## Phase 5: Frontend single-page app (about 3 to 4 hours)

Goal: a learner can finish the whole scene on a phone using only audio, pictures and two big buttons.

### State machine (`App.tsx`)

Keep it in one `useReducer`. State = current turn index, phase, attempt count for this turn, and the last evaluate response. Phases, in order:

1. `START`: one large play button. Tapping it unlocks audio playback (iPhone blocks audio until a tap) and asks for mic permission.
2. `HEAR`: the supervisor line plays automatically, then moves to `POINT`.
3. `POINT`: three pictures. Wrong tap → retry sound, the line replays slowly, the wrong picture fades. Right tap → correct sound, then `MODEL`.
4. `MODEL`: the model reply (`replies[0]`) plays, then `SAY`.
5. `SAY`: the mic button pulses until the learner holds it.
6. `EVALUATING`: a spinner while `/api/evaluate` runs.
7. `FEEDBACK`: shows the result (table below). Pass → next turn's `HEAR`, or `RECAP` after the last turn.
8. `RECAP`: every turn's correct picture with a play button for its model reply, and how many turns passed on the first try.

The repeat request is a side trip from `HEAR` or `POINT`: the learner holds the "repeat" button and says the phrase, which is evaluated with `turnId=repeat_request`. On a pass, the supervisor's slow line plays and the learner returns to `POINT`. Otherwise, the app plays the model phrase and lets them try again.

### Feedback by result

| Result | Color and sound | What the app does |
| --- | --- | --- |
| PASS | Green check, correct chime | Shows a big "next" arrow |
| CLOSE | Amber, soft tone | Shows the best reply's text with `focusWords` highlighted, plays that reply slowly, offers try again |
| RETRY | Muted red, soft tone | Replays the supervisor line slowly, then the model reply, then offers try again |
| NOT\_HEARD | Gray mic with a question mark | Plays the help clip for the turn, offers try again |

After 3 attempts on one turn, show a "continue" arrow next to "try again" so nobody gets stuck. Show the `tip` in small text under the feedback. It helps literate learners but the screen must make sense without it.

### Components

- `SupervisorCard`: a supervisor picture, a replay button and a slow-replay button (a turtle icon works well).
- `PictureChoices`: three large tappable pictures, shuffled per turn, with a small English label under each.
- `MicButton`: hold to talk. `pointerdown` starts recording and `pointerup` stops. Ignore recordings under 0.4 seconds and auto-stop at 10 seconds.
- `RepeatButton`: same hold-to-talk behavior, with an "ear" or question icon.
- `HelpButton`: always visible in the corner. Plays `help_<turnId>.mp3`.
- `ProgressDots`: one dot per turn.
- `DebugPanel`: shown only with `?debug=1` in the URL. Displays the transcript, `source`, `issue` and timings. Also has a text box that sends a typed transcript as debugTranscript instead of a recording. Useful when demoing to the team.

### Audio helpers (`audio.ts`)

- `play(url)` returns a promise that resolves when playback ends, so the reducer can chain steps. Use one shared `Audio` element.
- Recording: call `getUserMedia({ audio: true })` once and reuse the stream. Pick the first supported type from `audio/webm;codecs=opus`, `audio/mp4`, or the browser default, and name the upload file with the matching extension.

### Layout

Mobile first: one column, max width 480 px, touch targets at least 64 px, no scrolling during a turn. Text is optional decoration, never the only way to understand a screen.

**Done when:** on a laptop browser you can play all six turns start to finish, every result type shows the right feedback (force them with `debugTranscript`), and the repeat request works from both `HEAR` and `POINT`.

## Phase 6: Integration and phone demo (about 1 to 2 hours)

Goal: the demo runs on a real phone and survives a live audience.

### Getting it onto a phone

Browsers only allow the microphone over HTTPS or on `localhost`, so opening your laptop's IP address from a phone will silently fail to record.

1. Start the backend and frontend as usual.
2. Install `cloudflared` and run `cloudflared tunnel --url http://localhost:5173`. It prints a temporary `trycloudflare.com` HTTPS link with no account needed.
3. Add that host to Vite's `server.allowedHosts` (or allow all hosts in dev), since newer Vite versions block unknown hosts.
4. Open the link on your phone. API calls go through Vite's `/api` proxy, so only one tunnel is needed.

### Test on real devices

- An iPhone in Safari: the most likely place for recording-format and audio-unlock bugs.
- An Android phone in Chrome.
- A laptop with `?debug=1` for showing the internals.

### Tune with real voices

Record about 10 attempts from a few people, including some accented speech and a few deliberately wrong answers. Use the debug panel to check:

- Whether the `NOT_HEARD` thresholds (`no_speech_prob` 0.6, `avg_logprob` -1.0) catch silence without rejecting quiet speakers. Adjust if needed.
- How often Whisper "corrects" a mispronounced word into the right one. Note examples: it's the evidence for the ML subteam's pronunciation work.
- Round-trip time. Aim for under 3 seconds per attempt on the laptop. If transcription is slow, try `base.en` and compare accuracy.

### Demo safety

- Pre-load the Whisper model before the demo starts (hit `/api/health` and do one warm-up attempt).
- If Wi-Fi or the tunnel fails, the laptop at `localhost` still works.
- If Gemini rate-limits mid-demo, the fallback keeps the flow going. The debug panel shows `source: fallback` so you can explain it.

**Done when:** someone who has never seen the app finishes all six turns on a phone without you touching it.

## Building it with Claude Code

Run one phase per session and check its "Done when" yourself before starting the next. Starting each session fresh keeps the context small and makes mistakes easy to trace to one phase.

A prompt that works for each phase:

```text
Read SPEC.md and CLAUDE.md. Implement Phase <N> only.
Before writing code, list the files you will create or change and any spec detail
you think is wrong or unclear. Wait for my OK.
When done, tell me exactly how to verify the Phase <N> "Done when" criteria.
```

Watch for these common drifts:

- Claude Code "helpfully" adding a database, auth or extra scenes. Point it back to the out-of-scope list.
- Hard-coding turn content in React components instead of reading `scene.json`.
- Passing the expected reply to Whisper as `initial_prompt` to "improve accuracy".
- Sending audio to Gemini instead of the transcript.
- Guessing Piper or faster-whisper flags. Ask it to check the installed version's docs.

### Demo checklist

- [ ] Backend health shows `whisperLoaded: true` and the expected `geminiEnabled`
- [ ] All six turns play start to finish on a laptop
- [ ] Every result type (PASS, CLOSE, RETRY, NOT\_HEARD) shows the right feedback
- [ ] Turn t6 passes both "No, thank you" and "Where is the bathroom?"
- [ ] The repeat request works from both the hear and point steps
- [ ] The app keeps working with the Gemini key removed
- [ ] Recording works on an iPhone and an Android phone through the tunnel
- [ ] Every Rohingya clip is audibly labeled as a placeholder
- [ ] Round trip under about 3 seconds after warm-up
