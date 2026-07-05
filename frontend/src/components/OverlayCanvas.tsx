import { useEffect, useRef } from 'react';
import type { Box } from '../types/messages';

export function OverlayCanvas({ boxes, width, height }: { boxes: Box[]; width: number; height: number }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const c = ref.current;
    if (!c) return;
    const ctx = c.getContext('2d')!;
    const draw = () => {
      c.width = c.clientWidth;
      c.height = c.clientHeight;
      ctx.clearRect(0, 0, c.width, c.height);
      const sourceAspect = Math.max(1, width) / Math.max(1, height);
      const canvasAspect = c.width / Math.max(1, c.height);
      const drawWidth = canvasAspect > sourceAspect ? c.height * sourceAspect : c.width;
      const drawHeight = canvasAspect > sourceAspect ? c.height : c.width / sourceAspect;
      const offsetX = (c.width - drawWidth) / 2;
      const offsetY = (c.height - drawHeight) / 2;
      const scale = drawWidth / Math.max(1, width);
      ctx.lineWidth = 2;
      ctx.font = '14px sans-serif';
      boxes.forEach(b => {
        const x = offsetX + b.x * scale;
        const y = offsetY + b.y * scale;
        ctx.strokeStyle = '#00ff88';
        ctx.fillStyle = '#00ff88';
        ctx.strokeRect(x, y, b.w * scale, b.h * scale);
        ctx.fillText(`${b.label} ${b.score.toFixed(2)}`, x, Math.max(16, y - 4));
      });
    };
    const id = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(id);
  }, [boxes, width, height]);
  return <canvas ref={ref} className="overlay" />;
}
