import type { EventMessage } from '../types/messages';
import { API_BASE } from './restClient';

export function connectEvents(onMessage: (message: EventMessage) => void, onState: (state: string) => void): () => void {
  let closed = false; let ws: WebSocket | null = null; let timer = 0;
  const open = () => { const url = API_BASE.replace(/^http/, 'ws') + '/ws/events'; ws = new WebSocket(url); onState('连接中'); ws.onopen = () => onState('已连接'); ws.onmessage = ev => onMessage(JSON.parse(ev.data)); ws.onclose = () => { onState('已断开，准备重连'); if (!closed) timer = window.setTimeout(open, 1500); }; ws.onerror = () => onState('连接错误'); };
  open(); return () => { closed = true; window.clearTimeout(timer); ws?.close(); };
}
