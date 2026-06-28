import { useEffect, useState } from 'react';
import { api } from './api/restClient';
import { connectEvents } from './api/wsClient';
import { ControlPanel } from './components/ControlPanel';
import { LogPanel } from './components/LogPanel';
import { MetricsPanel } from './components/MetricsPanel';
import { SpectrumCanvas } from './components/SpectrumCanvas';
import { VideoPanel } from './components/VideoPanel';
import { WaveformCanvas } from './components/WaveformCanvas';
import type { AppSettings, Device } from './types/settings';
import type { Box, EventMessage } from './types/messages';
import './styles/app.css';

export default function App() {
  const [settings, setSettings] = useState<AppSettings | null>(null); const [saved, setSaved] = useState<AppSettings | null>(null); const [status, setStatus] = useState<any>(null); const [videoDevices, setVideoDevices] = useState<Device[]>([]); const [audioDevices, setAudioDevices] = useState<Device[]>([]); const [boxes, setBoxes] = useState<Box[]>([]); const [metrics, setMetrics] = useState<any>(null); const [wave, setWave] = useState<number[]>([]); const [spectrum, setSpectrum] = useState<number[]>([]); const [audio, setAudio] = useState<any>(null); const [logs, setLogs] = useState<string[]>([]); const [wsState, setWsState] = useState('未连接');
  const refresh = async () => { const [s, st, vd, ad] = await Promise.all([api.settings(), api.status(), api.videoDevices(), api.audioDevices()]); setSettings(s); setSaved(s); setStatus(st); setVideoDevices(vd.devices); setAudioDevices(ad.devices); };
  useEffect(() => { refresh(); const timer = setInterval(()=>api.status().then(setStatus).catch(()=>{}), 2000); const close = connectEvents((m: EventMessage) => { if (m.type === 'detection.boxes') setBoxes(m.boxes); if (m.type === 'video.metrics') setMetrics(m); if (m.type === 'audio.waveform') setWave(m.values); if (m.type === 'audio.spectrum') setSpectrum(m.magnitudes); if (m.type === 'audio.metrics') setAudio(m); if (m.type === 'log') setLogs(l => [...l.slice(-199), `${new Date(m.timestamp).toLocaleTimeString()} [${m.level}] ${m.message}`]); }, setWsState); return () => { clearInterval(timer); close(); }; }, []);
  const save = async () => { if (!settings) return; await api.saveSettings(settings); setSaved(settings); setLogs(l=>[...l.slice(-199),'设置已保存，请确认后重启管线使其生效。']); };
  const restart = async () => { if (!confirm('确认重启管线并应用当前设置？')) return; setStatus(await api.restart()); };
  const dirty = JSON.stringify(settings) !== JSON.stringify(saved);
  return <main><header><h1>局域网 USB 摄像头图像/音频算法实验台</h1><span>WebSocket：{wsState}</span></header><div className="dashboard"><VideoPanel url={settings?.mediamtx_webrtc_url ?? ''} boxes={boxes} width={metrics?.width ?? settings?.video_width ?? 1280} height={metrics?.height ?? settings?.video_height ?? 720}/><ControlPanel settings={settings} setSettings={setSettings} videoDevices={videoDevices} audioDevices={audioDevices} onRefresh={refresh} onSave={save} onStart={async()=>setStatus(await api.start())} onStop={async()=>setStatus(await api.stop())} onRestart={restart} dirty={dirty}/><section className="card"><h2>音频波形</h2><WaveformCanvas values={wave}/></section><MetricsPanel status={status} metrics={metrics} audio={audio}/><section className="card"><h2>音频频谱</h2><SpectrumCanvas magnitudes={spectrum}/></section><LogPanel logs={logs}/></div></main>;
}
