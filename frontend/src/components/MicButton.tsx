import type { Recording } from '../audio'
import HoldToTalkButton from './HoldToTalkButton'

interface Props {
  disabled?: boolean
  onRecorded: (recording: Recording | null) => void
}

export default function MicButton({ disabled, onRecorded }: Props) {
  return (
    <HoldToTalkButton
      label="Hold to talk"
      icon="🎤"
      pulsing
      disabled={disabled}
      onRecorded={onRecorded}
    />
  )
}
