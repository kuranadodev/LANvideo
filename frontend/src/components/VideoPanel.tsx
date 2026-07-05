import { OverlayCanvas } from './OverlayCanvas';
import type { Box } from '../types/messages';
export function VideoPanel({ url, boxes, width, height }: { url: string; boxes: Box[]; width: number; height: number }) { return <section className="card video-card"><h2>实时视频监看</h2><div className="video-wrap"><iframe title="MediaMTX WebRTC" src={url} /><OverlayCanvas boxes={boxes} width={width} height={height} /></div><p className="hint">视频由 MediaMTX WebRTC 页面显示，算法框与标签由前端 Canvas 叠加。</p></section>; }
