import type { AppSettings, Device } from '../types/settings';

export function ControlPanel({ settings, setSettings, videoDevices, audioDevices, onRefresh, onSave, onStart, onStop, onRestart, dirty }: { settings: AppSettings | null; setSettings: (s: AppSettings) => void; videoDevices: Device[]; audioDevices: Device[]; onRefresh: () => void; onSave: () => void; onStart: () => void; onStop: () => void; onRestart: () => void; dirty: boolean }) {
  if (!settings) return <section className="card"><h2>控制面板</h2>加载中...</section>;
  const update = (patch: Partial<AppSettings>) => setSettings({ ...settings, ...patch });
  return <section className="card"><h2>控制面板</h2>
    <label>视频设备<select value={settings.video_device} onChange={e=>update({video_device:e.target.value})}>{videoDevices.map(d=><option key={String(d.id)} value={String(d.id)} disabled={!d.available}>{d.name} ({String(d.id)})</option>)}</select></label>
    <label>音频设备<select value={settings.audio_device == null ? '' : String(settings.audio_device)} onChange={e=>update({audio_device:e.target.value === '' ? null : Number.isNaN(Number(e.target.value)) ? e.target.value : Number(e.target.value)})}><option value="">默认设备</option>{audioDevices.map(d=><option key={String(d.id)} value={String(d.id ?? '')} disabled={!d.available}>{d.name}</option>)}</select></label>
    <div className="grid2"><label>宽度<input type="number" value={settings.video_width} onChange={e=>update({video_width:Number(e.target.value)})}/></label><label>高度<input type="number" value={settings.video_height} onChange={e=>update({video_height:Number(e.target.value)})}/></label><label>FPS<input type="number" value={settings.video_fps} onChange={e=>update({video_fps:Number(e.target.value)})}/></label><label>音频采样率<input type="number" value={settings.audio_sample_rate} onChange={e=>update({audio_sample_rate:Number(e.target.value)})}/></label><label>音频块大小<input type="number" value={settings.audio_block_size} onChange={e=>update({audio_block_size:Number(e.target.value)})}/></label><label>视频算法<select value={settings.video_algorithm} onChange={e=>update({video_algorithm:e.target.value})}><option value="dummy">dummy</option><option value="motion">motion</option></select></label></div>
    {dirty && <p className="warn">设置已修改，保存后需要重启管线生效。</p>}
    <div className="buttons"><button onClick={onRefresh}>刷新设备</button><button onClick={onSave}>保存设置</button><button onClick={onStart}>启动管线</button><button onClick={onStop}>停止管线</button><button onClick={onRestart}>重启管线</button></div>
  </section>;
}
