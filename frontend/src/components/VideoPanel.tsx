import { OverlayCanvas } from './OverlayCanvas';
import type { Box } from '../types/messages';
export function VideoPanel({ url, boxes, width, height }: { url: string; boxes: Box[]; width: number; height: number }) { return <section className="card video-card"><h2>实时处理后视频</h2><div className="video-wrap"><iframe title="MediaMTX WebRTC" src={url} /><OverlayCanvas boxes={boxes} width={width} height={height} /></div><p className="hint">视频由 MediaMTX WebRTC 页面以 iframe 显示。</p></section>; }
