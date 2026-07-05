export type Box = { x: number; y: number; w: number; h: number; label: string; score: number };
export type EventMessage =
  | { type: 'video.metrics'; timestamp: number; fps: number; analysis_fps?: number; frame_index: number; algorithm_ms: number; width: number; height: number }
  | { type: 'detection.boxes'; timestamp: number; frame_index: number; boxes: Box[]; source_width?: number; source_height?: number }
  | { type: 'audio.waveform'; timestamp: number; sample_rate: number; values: number[] }
  | { type: 'audio.spectrum'; timestamp: number; sample_rate: number; freqs: number[]; magnitudes: number[] }
  | { type: 'audio.metrics'; timestamp: number; rms: number; peak: number }
  | { type: 'log'; timestamp: number; level: string; message: string };
