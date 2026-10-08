// Switch this to 'png' in one place once real pictograms replace the placeholder SVGs.
export const IMAGE_EXT = 'svg'

export const audioUrl = (id: string) => `/scene/audio/${id}.mp3`
export const slowAudioUrl = (id: string) => `/scene/audio/${id}_slow.mp3`
export const helpAudioUrl = (turnId: string) => `/scene/audio/help_${turnId}.mp3`
export const imageUrl = (optionId: string) => `/scene/images/${optionId}.${IMAGE_EXT}`
export const sfxUrl = (name: 'correct' | 'retry') => `/scene/sfx/${name}.mp3`
