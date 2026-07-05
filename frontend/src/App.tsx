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
import type { Box, EventMessage, WebRtcStats } from './types/messages';
import './styles/app.css';

type BusyAction = 'refresh' | 'start' | 'stop' | null;

export default function App() {
  const [settings, setSettings] = useState<AppSettings | null>(null); const [saved, setSaved] = useState<AppSettings | null>(null); const [status, setStatus] = useState<any>(null); const [videoDevices, setVideoDevices] = useState<Device[]>([]); const [audioDevices, setAudioDevices] = useState<Device[]>([]); const [boxes, setBoxes] = useState<Box[]>([]); const [boxSource, setBoxSource] = useState({ width: 1280, height: 720 }); const [metrics, setMetrics] = useState<any>(null); const [wave, setWave] = useState<number[]>([]); const [spectrum, setSpectrum] = useState<number[]>([]); const [audio, setAudio] = useState<any>(null); const [logs, setLogs] = useState<string[]>([]); const [wsState, setWsState] = useState('未连接'); const [busyAction, setBusyAction] = useState<BusyAction>(null); const [webRtcStats, setWebRtcStats] = useState<WebRtcStats | null>(null); const [errorMessage, setErrorMessage] = useState<string | null>(null); const [playerVersion, setPlayerVersion] = useState(0);
  const refresh = async () => { const [s, st, vd, ad] = await Promise.all([api.settings(), api.status(), api.videoDevices(), api.audioDevices()]); setSettings(s); setSaved(s); setStatus(st); setVideoDevices(vd.devices); setAudioDevices(ad.devices); };
  const refreshDevices = async () => { setBusyAction('refresh'); setErrorMessage(null); try { const [st, vd, ad] = await Promise.all([api.status(), api.videoDevices(), api.audioDevices()]); setStatus(st); setVideoDevices(vd.devices); setAudioDevices(ad.devices); setLogs(l=>[...l.slice(-199),'设备列表已刷新。']); } catch (error) { setErrorMessage(error instanceof Error ? error.message : String(error)); } finally { setBusyAction(null); } };
  useEffect(() => { refresh().catch(error => setErrorMessage(error instanceof Error ? error.message : String(error))); const timer = setInterval(()=>api.status().then(setStatus).catch(()=>{}), 2000); const close = connectEvents((m: EventMessage) => { if (m.type === 'detection.boxes') { setBoxes(m.boxes); setBoxSource(prev => ({ width: m.source_width ?? prev.width, height: m.source_height ?? prev.height })); } if (m.type === 'video.metrics') setMetrics(m); if (m.type === 'audio.waveform') setWave(m.values); if (m.type === 'audio.spectrum') setSpectrum(m.magnitudes); if (m.type === 'audio.metrics') setAudio(m); if (m.type === 'log') setLogs(l => [...l.slice(-199), `${new Date(m.timestamp).toLocaleTimeString()} [${m.level}] ${m.message}`]); }, setWsState); return () => { clearInterval(timer); close(); }; }, []);
  const start = async () => { if (!settings) return; setBusyAction('start'); setErrorMessage(null); try { const nextStatus = await api.applyStart(settings); setSaved(settings); setStatus(nextStatus); setPlayerVersion(version => version + 1); setLogs(l=>[...l.slice(-199),'已应用当前设置并启动管线。']); } catch (error) { setErrorMessage(error instanceof Error ? error.message : String(error)); } finally { setBusyAction(null); } };
  const stop = async () => { setBusyAction('stop'); setErrorMessage(null); try { setStatus(await api.stop()); setLogs(l=>[...l.slice(-199),'管线已停止。']); } catch (error) { setErrorMessage(error instanceof Error ? error.message : String(error)); } finally { setBusyAction(null); } };
  const dirty = JSON.stringify(settings) !== JSON.stringify(saved);
  const isVideoRunning = status?.video?.running === true;
  const playerKey = `${playerVersion}-${isVideoRunning ? 'running' : 'stopped'}-${settings?.mediamtx_webrtc_url ?? ''}`;
  return <main><header><h1>局域网 USB 摄像头图像/音频算法实验台</h1><span>WebSocket：{wsState}</span></header><div className="dashboard"><VideoPanel url={settings?.mediamtx_webrtc_url ?? ''} boxes={boxes} width={boxSource.width} height={boxSource.height} isVideoRunning={isVideoRunning} playerKey={playerKey} onStats={setWebRtcStats}/><ControlPanel settings={settings} setSettings={setSettings} videoDevices={videoDevices} audioDevices={audioDevices} onRefresh={refreshDevices} onStart={start} onStop={stop} dirty={dirty} busyAction={busyAction} errorMessage={errorMessage}/><section className="card"><h2>音频波形</h2><WaveformCanvas values={wave}/></section><MetricsPanel status={status} metrics={metrics} audio={audio} webRtcStats={webRtcStats}/><section className="card"><h2>音频频谱</h2><SpectrumCanvas magnitudes={spectrum}/></section><LogPanel logs={logs}/></div></main>;
}
