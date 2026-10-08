const MIME_CANDIDATES: Array<{ mimeType: string; extension: string }> = [
  { mimeType: 'audio/webm;codecs=opus', extension: 'webm' },
  { mimeType: 'audio/mp4', extension: 'mp4' },
]

function pickMimeType(): { mimeType: string; extension: string } {
  for (const candidate of MIME_CANDIDATES) {
    if (typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported(candidate.mimeType)) {
      return candidate
    }
  }
  return { mimeType: '', extension: 'webm' }
}

let sharedStream: MediaStream | null = null
let mediaRecorder: MediaRecorder | null = null
let chunks: BlobPart[] = []
let recordStartTime = 0
let activeMimeType = ''

export async function ensureMicAccess(): Promise<void> {
  if (!sharedStream) {
    sharedStream = await navigator.mediaDevices.getUserMedia({ audio: true })
  }
}

export function hasMicAccess(): boolean {
  return sharedStream !== null
}

export function startRecording(): void {
  if (!sharedStream) {
    throw new Error('Mic not initialized; call ensureMicAccess() first')
  }
  const { mimeType } = pickMimeType()
  activeMimeType = mimeType
  chunks = []
  mediaRecorder = mimeType ? new MediaRecorder(sharedStream, { mimeType }) : new MediaRecorder(sharedStream)
  mediaRecorder.ondataavailable = (e) => {
    if (e.data.size > 0) chunks.push(e.data)
  }
  mediaRecorder.start()
  recordStartTime = performance.now()
}

export interface Recording {
  blob: Blob
  fileName: string
}

const MIN_RECORDING_MS = 400

export function stopRecording(): Promise<Recording | null> {
  return new Promise((resolve) => {
    const recorder = mediaRecorder
    if (!recorder || recorder.state === 'inactive') {
      resolve(null)
      return
    }
    recorder.onstop = () => {
      const durationMs = performance.now() - recordStartTime
      mediaRecorder = null
      if (durationMs < MIN_RECORDING_MS) {
        resolve(null)
        return
      }
      const extension = activeMimeType.includes('mp4') ? 'mp4' : 'webm'
      const blob = new Blob(chunks, { type: activeMimeType || 'audio/webm' })
      resolve({ blob, fileName: `recording.${extension}` })
    }
    recorder.stop()
  })
}

export function isRecording(): boolean {
  return mediaRecorder !== null && mediaRecorder.state === 'recording'
}

const sharedAudio = new Audio()

export function play(url: string): Promise<void> {
  return new Promise((resolve, reject) => {
    sharedAudio.pause()
    sharedAudio.src = url
    const cleanup = () => {
      sharedAudio.removeEventListener('ended', onEnded)
      sharedAudio.removeEventListener('error', onError)
    }
    const onEnded = () => {
      cleanup()
      resolve()
    }
    const onError = () => {
      cleanup()
      reject(new Error(`Failed to play ${url}`))
    }
    sharedAudio.addEventListener('ended', onEnded)
    sharedAudio.addEventListener('error', onError)
    sharedAudio.play().catch(onError)
  })
}

export function unlockAudioPlayback(): void {
  sharedAudio.play().catch(() => {
    /* ignore: this call exists only to satisfy the browser's user-gesture unlock requirement */
  })
  sharedAudio.pause()
  sharedAudio.currentTime = 0
}
