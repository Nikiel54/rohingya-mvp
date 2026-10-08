export interface SceneLine {
  id: string;
  text: string;
}

export interface PointOption {
  id: string;
  label: string;
}

export interface PointStep {
  options: PointOption[];
  correct: string;
}

export interface SayReply {
  id: string;
  text: string;
}

export interface SayStep {
  intent: string;
  keyWords: string[];
  replies: SayReply[];
}

export interface Turn {
  id: string;
  line: SceneLine;
  point: PointStep;
  say: SayStep;
}

export interface RepeatRequest {
  id: string;
  text: string;
  accepted: string[];
}

export interface Scene {
  id: string;
  title: string;
  repeatRequest: RepeatRequest;
  turns: Turn[];
}

export type EvaluateResult = "PASS" | "CLOSE" | "RETRY" | "NOT_HEARD";
export type EvaluateSource = "speech_check" | "fuzzy" | "gemini" | "fallback";
export type EvaluateIssue =
  | "none"
  | "missing_key_word"
  | "wrong_meaning"
  | "off_topic"
  | "unclear_speech";

export interface EvaluateResponse {
  result: EvaluateResult;
  transcript: string;
  source: EvaluateSource;
  issue: EvaluateIssue;
  focusWords: string[];
  bestReplyId: string | null;
  tip: string | null;
  unclearWords: string[];
  timingsMs: {
    transcribe: number;
    judge: number;
  };
}

export interface HealthResponse {
  ok: boolean;
  whisperLoaded: boolean;
  geminiEnabled: boolean;
}
