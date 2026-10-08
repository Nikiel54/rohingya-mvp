import type { PointOption } from '../types'
import { imageUrl } from '../sceneAssets'

interface Props {
  options: PointOption[]
  wrongIds: string[]
  disabled: boolean
  onSelect: (optionId: string) => void
}

export default function PictureChoices({ options, wrongIds, disabled, onSelect }: Props) {
  return (
    <div className="picture-choices">
      {options.map((opt) => {
        const isWrong = wrongIds.includes(opt.id)
        return (
          <button
            key={opt.id}
            type="button"
            className={`picture-choice${isWrong ? ' picture-choice--wrong' : ''}`}
            disabled={disabled || isWrong}
            onClick={() => onSelect(opt.id)}
          >
            <img src={imageUrl(opt.id)} alt={opt.label} />
            <span>{opt.label}</span>
          </button>
        )
      })}
    </div>
  )
}
