import { useRef, useState } from 'react'
import { ensureMicAccess, startRecording, stopRecording, type Recording } from '../audio'

const MAX_RECORDING_MS = 10000

interface Props {
  label: string
  icon: string
  pulsing?: boolean
  disabled?: boolean
  onRecorded: (recording: Recording | null) => void
}

export default function HoldToTalkButton({ label, icon, pulsing, disabled, onRecorded }: Props) {
  const [recording, setRecording] = useState(false)
  const autoStopTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const startedRef = useRef(false)

  async function handleDown() {
    if (disabled || startedRef.current) return
    startedRef.current = true
    try {
      await ensureMicAccess()
      startRecording()
      setRecording(true)
      autoStopTimer.current = setTimeout(() => {
        void handleUp()
      }, MAX_RECORDING_MS)
    } catch {
      startedRef.current = false
    }
  }

  async function handleUp() {
    if (!startedRef.current) return
    startedRef.current = false
    if (autoStopTimer.current) {
      clearTimeout(autoStopTimer.current)
      autoStopTimer.current = null
    }
    setRecording(false)
    const result = await stopRecording()
    onRecorded(result)
  }

  return (
    <button
      type="button"
      className={`hold-to-talk${recording ? ' hold-to-talk--recording' : ''}${pulsing ? ' hold-to-talk--pulsing' : ''}`}
      disabled={disabled}
      aria-label={label}
      onPointerDown={handleDown}
      onPointerUp={handleUp}
      onPointerLeave={handleUp}
      onPointerCancel={handleUp}
    >
      <span className="hold-to-talk__icon">{icon}</span>
      <span className="hold-to-talk__label">{label}</span>
    </button>
  )
}
