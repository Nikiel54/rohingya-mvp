import type { Recording } from '../audio'
import HoldToTalkButton from './HoldToTalkButton'

interface Props {
  disabled?: boolean
  onRecorded: (recording: Recording | null) => void
}

export default function RepeatButton({ disabled, onRecorded }: Props) {
  return (
    <HoldToTalkButton
      label="Can you repeat that, please?"
      icon="👂"
      disabled={disabled}
      onRecorded={onRecorded}
    />
  )
}
