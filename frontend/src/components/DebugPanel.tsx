import { useState } from 'react'
import type { EvaluateResponse } from '../types'

interface Props {
  lastResponse: EvaluateResponse | null
  onSubmitDebugTranscript: (text: string) => void
}

export default function DebugPanel({ lastResponse, onSubmitDebugTranscript }: Props) {
  const [text, setText] = useState('')

  return (
    <div className="debug-panel">
      <h3>Debug</h3>
      {lastResponse ? (
        <dl>
          <dt>transcript</dt>
          <dd>{lastResponse.transcript || '(empty)'}</dd>
          <dt>source</dt>
          <dd>{lastResponse.source}</dd>
          <dt>issue</dt>
          <dd>{lastResponse.issue}</dd>
          <dt>result</dt>
          <dd>{lastResponse.result}</dd>
          <dt>timingsMs</dt>
          <dd>
            transcribe={lastResponse.timingsMs.transcribe} judge={lastResponse.timingsMs.judge}
          </dd>
        </dl>
      ) : (
        <p>No evaluation yet.</p>
      )}
      <form
        onSubmit={(e) => {
          e.preventDefault()
          onSubmitDebugTranscript(text)
        }}
      >
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Type a transcript to force an evaluate()"
        />
        <button type="submit">Send</button>
      </form>
    </div>
  )
}
