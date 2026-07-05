import { useCallback } from 'react';
import { OverlayCanvas } from './OverlayCanvas';
import { WebRtcPlayer } from './WebRtcPlayer';
import type { Box, WebRtcStats } from '../types/messages';

export function VideoPanel({ url, boxes, width, height, onStats }: { url: string; boxes: Box[]; width: number; height: number; onStats: (stats: WebRtcStats | null) => void }) {
  const handleStats = useCallback((stats: WebRtcStats | null) => onStats(stats), [onStats]);
  return <section className="card video-card"><h2>实时视频监看</h2><div className="video-wrap"><WebRtcPlayer url={url} onStats={handleStats} /><OverlayCanvas boxes={boxes} width={width} height={height} /></div><p className="hint">视频由原生 WebRTC 播放，算法框与标签由前端 Canvas 叠加。</p></section>;
}
