interface Props {
  total: number
  currentIndex: number
  passedFirstTry: boolean[]
}

export default function ProgressDots({ total, currentIndex, passedFirstTry }: Props) {
  return (
    <div className="progress-dots">
      {Array.from({ length: total }, (_, i) => {
        let className = 'progress-dot'
        if (i < currentIndex) {
          className += passedFirstTry[i] ? ' progress-dot--pass' : ' progress-dot--done'
        } else if (i === currentIndex) {
          className += ' progress-dot--current'
        }
        return <span key={i} className={className} />
      })}
    </div>
  )
}
