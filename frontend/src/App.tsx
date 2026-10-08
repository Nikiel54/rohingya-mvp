import { useEffect, useMemo, useReducer, useState } from 'react'
import { evaluate } from './api'
import { ensureMicAccess, play, unlockAudioPlayback, type Recording } from './audio'
import DebugPanel from './components/DebugPanel'
import HelpButton from './components/HelpButton'
import MicButton from './components/MicButton'
import PictureChoices from './components/PictureChoices'
import ProgressDots from './components/ProgressDots'
import RepeatButton from './components/RepeatButton'
import SupervisorCard from './components/SupervisorCard'
import { audioUrl, helpAudioUrl, imageUrl, sfxUrl, slowAudioUrl } from './sceneAssets'
import type { EvaluateResponse, Scene } from './types'
import { shuffle } from './util'
import './App.css'

type Phase = 'START' | 'HEAR' | 'POINT' | 'MODEL' | 'SAY' | 'EVALUATING' | 'FEEDBACK' | 'RECAP'

interface AppState {
  phase: Phase
  turnIndex: number
  attempt: number
  lastResponse: EvaluateResponse | null
  wrongOptionIds: string[]
  passedFirstTry: boolean[]
}

type Action =
  | { type: 'STARTED' }
  | { type: 'HEAR_ENDED' }
  | { type: 'POINT_WRONG'; optionId: string }
  | { type: 'POINT_CORRECT' }
  | { type: 'MODEL_ENDED' }
  | { type: 'EVALUATING' }
  | { type: 'EVAL_RESULT'; response: EvaluateResponse }
  | { type: 'TRY_AGAIN' }
  | { type: 'ADVANCE'; totalTurns: number }
  | { type: 'GOTO_POINT' }

const initialState: AppState = {
  phase: 'START',
  turnIndex: 0,
  attempt: 0,
  lastResponse: null,
  wrongOptionIds: [],
  passedFirstTry: [],
}

function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case 'STARTED':
      return { ...state, phase: 'HEAR' }
    case 'HEAR_ENDED':
      return { ...state, phase: 'POINT' }
    case 'POINT_WRONG':
      return { ...state, wrongOptionIds: [...state.wrongOptionIds, action.optionId] }
    case 'POINT_CORRECT':
      return { ...state, phase: 'MODEL' }
    case 'MODEL_ENDED':
      return { ...state, phase: 'SAY' }
    case 'EVALUATING':
      return { ...state, phase: 'EVALUATING' }
    case 'EVAL_RESULT': {
      const attempt = state.attempt + 1
      const passedFirstTry = [...state.passedFirstTry]
      if (action.response.result === 'PASS') {
        passedFirstTry[state.turnIndex] = attempt === 1
      }
      return { ...state, phase: 'FEEDBACK', attempt, lastResponse: action.response, passedFirstTry }
    }
    case 'TRY_AGAIN':
      return { ...state, phase: 'SAY' }
    case 'ADVANCE': {
      const passedFirstTry = [...state.passedFirstTry]
      if (passedFirstTry[state.turnIndex] === undefined) passedFirstTry[state.turnIndex] = false
      if (state.turnIndex + 1 >= action.totalTurns) {
        return { ...state, phase: 'RECAP', passedFirstTry }
      }
      return {
        ...state,
        phase: 'HEAR',
        turnIndex: state.turnIndex + 1,
        attempt: 0,
        wrongOptionIds: [],
        lastResponse: null,
        passedFirstTry,
      }
    }
    case 'GOTO_POINT':
      return { ...state, phase: 'POINT', wrongOptionIds: [] }
    default:
      return state
  }
}

function useScene() {
  const [scene, setScene] = useState<Scene | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/scene/scene.json')
      .then((res) => {
        if (!res.ok) throw new Error(`Failed to load scene.json: ${res.status}`)
        return res.json()
      })
      .then(setScene)
      .catch((err) => setError(String(err)))
  }, [])

  return { scene, error }
}

function App() {
  const { scene, error: sceneError } = useScene()
  const [state, dispatch] = useReducer(reducer, initialState)
  const [repeatBusy, setRepeatBusy] = useState(false)
  const debugMode = new URLSearchParams(window.location.search).get('debug') === '1'

  const currentTurn = scene ? scene.turns[state.turnIndex] : null

  const shuffledOptions = useMemo(() => {
    if (!currentTurn) return []
    return shuffle(currentTurn.point.options)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentTurn?.id])

  // HEAR: autoplay the supervisor's line, then move on.
  useEffect(() => {
    if (state.phase !== 'HEAR' || !currentTurn) return
    let cancelled = false
    play(audioUrl(currentTurn.line.id))
      .catch(() => {})
      .finally(() => {
        if (!cancelled) dispatch({ type: 'HEAR_ENDED' })
      })
    return () => {
      cancelled = true
    }
  }, [state.phase, currentTurn])

  // MODEL: autoplay the model reply, then let the learner speak.
  useEffect(() => {
    if (state.phase !== 'MODEL' || !currentTurn) return
    let cancelled = false
    play(audioUrl(currentTurn.say.replies[0].id))
      .catch(() => {})
      .finally(() => {
        if (!cancelled) dispatch({ type: 'MODEL_ENDED' })
      })
    return () => {
      cancelled = true
    }
  }, [state.phase, currentTurn])

  // FEEDBACK: play the sound/audio that matches the result.
  useEffect(() => {
    if (state.phase !== 'FEEDBACK' || !state.lastResponse || !currentTurn) return
    let cancelled = false
    const { result, bestReplyId } = state.lastResponse
    const turn = currentTurn

    async function run() {
      if (result === 'PASS') {
        await play(sfxUrl('correct'))
      } else if (result === 'CLOSE') {
        await play(sfxUrl('retry'))
        if (!cancelled && bestReplyId) await play(slowAudioUrl(bestReplyId))
      } else if (result === 'RETRY') {
        await play(sfxUrl('retry'))
        if (!cancelled) await play(slowAudioUrl(turn.line.id))
        if (!cancelled) await play(audioUrl(turn.say.replies[0].id))
      } else if (result === 'NOT_HEARD') {
        if (!cancelled) await play(helpAudioUrl(turn.id))
      }
    }

    run().catch(() => {})
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.phase, state.attempt])

  async function handleStart() {
    unlockAudioPlayback()
    try {
      await ensureMicAccess()
    } catch {
      // Mic permission may be denied; recording attempts will simply fail later.
    }
    dispatch({ type: 'STARTED' })
  }

  function handlePointSelect(optionId: string) {
    if (!currentTurn) return
    if (optionId === currentTurn.point.correct) {
      dispatch({ type: 'POINT_CORRECT' })
    } else {
      dispatch({ type: 'POINT_WRONG', optionId })
      play(slowAudioUrl(currentTurn.line.id)).catch(() => {})
    }
  }

  async function runEvaluate(turnId: string, recording: Recording | null, debugTranscript?: string) {
    dispatch({ type: 'EVALUATING' })
    try {
      const blob = recording ? recording.blob : new Blob([])
      const fileName = recording ? recording.fileName : 'debug.txt'
      const response = await evaluate(blob, fileName, turnId, debugTranscript)
      dispatch({ type: 'EVAL_RESULT', response })
    } catch {
      dispatch({
        type: 'EVAL_RESULT',
        response: {
          result: 'NOT_HEARD',
          transcript: '',
          source: 'fallback',
          issue: 'unclear_speech',
          focusWords: [],
          bestReplyId: null,
          tip: null,
          unclearWords: [],
          timingsMs: { transcribe: 0, judge: 0 },
        },
      })
    }
  }

  function handleMicRecorded(recording: Recording | null) {
    if (!recording || !currentTurn) return
    void runEvaluate(currentTurn.id, recording)
  }

  function handleDebugSubmit(text: string) {
    if (!currentTurn) return
    void runEvaluate(currentTurn.id, null, text)
  }

  async function handleRepeatRecorded(recording: Recording | null) {
    if (!recording || !scene || !currentTurn || repeatBusy) return
    setRepeatBusy(true)
    try {
      const response = await evaluate(recording.blob, recording.fileName, 'repeat_request')
      if (response.result === 'PASS') {
        await play(slowAudioUrl(currentTurn.line.id))
        dispatch({ type: 'GOTO_POINT' })
      } else {
        await play(audioUrl(scene.repeatRequest.id))
      }
    } catch {
      // ignore network errors on the repeat side-trip
    } finally {
      setRepeatBusy(false)
    }
  }

  if (sceneError) {
    return <div className="app-shell error">Failed to load scene: {sceneError}</div>
  }

  if (!scene || !currentTurn) {
    return <div className="app-shell">Loading…</div>
  }

  return (
    <div className="app-shell">
      {state.phase !== 'START' && state.phase !== 'RECAP' && (
        <>
          <ProgressDots
            total={scene.turns.length}
            currentIndex={state.turnIndex}
            passedFirstTry={state.passedFirstTry}
          />
          <HelpButton turnId={currentTurn.id} />
        </>
      )}

      {state.phase === 'START' && (
        <div className="screen screen--center">
          <h1>First Shift</h1>
          <button type="button" className="big-play-button" onClick={handleStart}>
            ▶ Start
          </button>
        </div>
      )}

      {(state.phase === 'HEAR' || state.phase === 'POINT') && (
        <div className="screen">
          <SupervisorCard lineId={currentTurn.line.id} text={currentTurn.line.text} />
          {state.phase === 'POINT' && (
            <PictureChoices
              options={shuffledOptions}
              wrongIds={state.wrongOptionIds}
              disabled={false}
              onSelect={handlePointSelect}
            />
          )}
          <RepeatButton disabled={repeatBusy} onRecorded={handleRepeatRecorded} />
        </div>
      )}

      {state.phase === 'MODEL' && (
        <div className="screen screen--center">
          <p className="model-reply-text">{currentTurn.say.replies[0].text}</p>
        </div>
      )}

      {state.phase === 'SAY' && (
        <div className="screen screen--center">
          <p className="model-reply-text">{currentTurn.say.replies[0].text}</p>
          <MicButton onRecorded={handleMicRecorded} />
        </div>
      )}

      {state.phase === 'EVALUATING' && (
        <div className="screen screen--center">
          <div className="spinner" aria-label="Evaluating" />
        </div>
      )}

      {state.phase === 'FEEDBACK' && state.lastResponse && (
        <FeedbackScreen
          response={state.lastResponse}
          turn={currentTurn}
          attempt={state.attempt}
          onTryAgain={() => dispatch({ type: 'TRY_AGAIN' })}
          onAdvance={() => dispatch({ type: 'ADVANCE', totalTurns: scene.turns.length })}
        />
      )}

      {state.phase === 'RECAP' && <RecapScreen scene={scene} passedFirstTry={state.passedFirstTry} />}

      {debugMode && <DebugPanel lastResponse={state.lastResponse} onSubmitDebugTranscript={handleDebugSubmit} />}
    </div>
  )
}

interface FeedbackScreenProps {
  response: EvaluateResponse
  turn: Scene['turns'][number]
  attempt: number
  onTryAgain: () => void
  onAdvance: () => void
}

function FeedbackScreen({ response, turn, attempt, onTryAgain, onAdvance }: FeedbackScreenProps) {
  const bestReply = turn.say.replies.find((r) => r.id === response.bestReplyId)
  const resultStyle: Record<string, { label: string; className: string; icon: string }> = {
    PASS: { label: 'Correct!', className: 'feedback--pass', icon: '✅' },
    CLOSE: { label: 'Almost', className: 'feedback--close', icon: '🟡' },
    RETRY: { label: 'Not quite', className: 'feedback--retry', icon: '🔸' },
    NOT_HEARD: { label: "Didn't catch that", className: 'feedback--not-heard', icon: '🎙️❓' },
  }
  const info = resultStyle[response.result]

  function highlightedReply() {
    if (!bestReply) return null
    const focusSet = new Set(response.focusWords.map((w) => w.toLowerCase()))
    return bestReply.text.split(/(\s+)/).map((word, i) => {
      const stripped = word.toLowerCase().replace(/[^\w']/g, '')
      const isFocus = focusSet.has(stripped)
      return isFocus ? (
        <strong key={i} className="focus-word">
          {word}
        </strong>
      ) : (
        <span key={i}>{word}</span>
      )
    })
  }

  return (
    <div className={`screen screen--center feedback ${info.className}`}>
      <div className="feedback-icon">{info.icon}</div>
      <h2>{info.label}</h2>
      {response.result === 'CLOSE' && bestReply && <p className="feedback-reply">{highlightedReply()}</p>}
      {response.tip && <p className="feedback-tip">{response.tip}</p>}
      <div className="feedback-actions">
        {response.result === 'PASS' ? (
          <button type="button" className="big-button" onClick={onAdvance}>
            Next →
          </button>
        ) : (
          <>
            <button type="button" className="big-button" onClick={onTryAgain}>
              Try again
            </button>
            {attempt >= 3 && (
              <button type="button" className="big-button big-button--secondary" onClick={onAdvance}>
                Continue →
              </button>
            )}
          </>
        )}
      </div>
    </div>
  )
}

function RecapScreen({ scene, passedFirstTry }: { scene: Scene; passedFirstTry: boolean[] }) {
  const passCount = passedFirstTry.filter(Boolean).length
  return (
    <div className="screen recap">
      <h1>Great work!</h1>
      <p>
        {passCount} of {scene.turns.length} turns passed on the first try.
      </p>
      <ul className="recap-list">
        {scene.turns.map((turn) => (
          <li key={turn.id} className="recap-item">
            <img src={imageUrl(turn.point.correct)} alt={turn.point.options.find((o) => o.id === turn.point.correct)?.label ?? ''} />
            <button type="button" className="icon-button" aria-label="Play model reply" onClick={() => play(audioUrl(turn.say.replies[0].id)).catch(() => {})}>
              🔊
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default App
