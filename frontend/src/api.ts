import type { EvaluateResponse, HealthResponse } from './types'

export async function getHealth(): Promise<HealthResponse> {
  const res = await fetch('/api/health')
  if (!res.ok) throw new Error(`health check failed: ${res.status}`)
  return res.json()
}

export async function evaluate(
  audio: Blob,
  fileName: string,
  turnId: string,
  debugTranscript?: string,
): Promise<EvaluateResponse> {
  const form = new FormData()
  form.append('audio', audio, fileName)
  form.append('turnId', turnId)
  if (debugTranscript) form.append('debugTranscript', debugTranscript)

  const res = await fetch('/api/evaluate', { method: 'POST', body: form })
  if (!res.ok) throw new Error(`evaluate failed: ${res.status}`)
  return res.json()
}
