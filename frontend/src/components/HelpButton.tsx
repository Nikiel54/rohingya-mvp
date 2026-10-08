import { play } from '../audio'
import { helpAudioUrl } from '../sceneAssets'

interface Props {
  turnId: string
}

export default function HelpButton({ turnId }: Props) {
  return (
    <button
      type="button"
      className="help-button"
      aria-label="Help in Rohingya"
      onClick={() => play(helpAudioUrl(turnId)).catch(() => {})}
    >
      ❓
    </button>
  )
}
