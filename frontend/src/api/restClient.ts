import type { AppSettings } from '../types/settings';

export const API_BASE = import.meta.env.VITE_API_BASE ?? `${location.protocol}//${location.hostname}:8000`;
async function json<T>(path: string, init?: RequestInit): Promise<T> { const res = await fetch(`${API_BASE}${path}`, { headers: { 'Content-Type': 'application/json' }, ...init }); if (!res.ok) { const text = await res.text(); let message = text; try { message = JSON.parse(text).detail ?? text; } catch {} throw new Error(message); } return res.json(); }
export const api = {
  status: () => json<any>('/api/status'),
  settings: () => json<AppSettings>('/api/settings'),
  saveSettings: (body: AppSettings) => json<any>('/api/settings', { method: 'POST', body: JSON.stringify(body) }),
  videoDevices: () => json<any>('/api/devices/video'),
  audioDevices: () => json<any>('/api/devices/audio'),
  start: () => json<any>('/api/pipeline/start', { method: 'POST' }),
  applyStart: (body: AppSettings) => json<any>('/api/pipeline/apply-start', { method: 'POST', body: JSON.stringify(body) }),
  stop: () => json<any>('/api/pipeline/stop', { method: 'POST' }),
  restart: () => json<any>('/api/pipeline/restart', { method: 'POST' }),
  videoAlgorithms: () => json<any>('/api/algorithms/video'),
  audioAlgorithms: () => json<any>('/api/algorithms/audio'),
};
