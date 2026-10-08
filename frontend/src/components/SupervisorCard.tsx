import { play } from '../audio'
import { audioUrl, slowAudioUrl } from '../sceneAssets'

interface Props {
  lineId: string
  text: string
}

export default function SupervisorCard({ lineId, text }: Props) {
  return (
    <div className="supervisor-card">
      <div className="supervisor-avatar" aria-hidden="true">
        🧑‍🏭
      </div>
      <p className="supervisor-text">{text}</p>
      <div className="supervisor-controls">
        <button
          type="button"
          className="icon-button"
          aria-label="Replay"
          onClick={() => play(audioUrl(lineId)).catch(() => {})}
        >
          🔊
        </button>
        <button
          type="button"
          className="icon-button"
          aria-label="Replay slowly"
          onClick={() => play(slowAudioUrl(lineId)).catch(() => {})}
        >
          🐢
        </button>
      </div>
    </div>
  )
}
