import type { AppSettings, Device } from '../types/settings';

const lowLatencyPreset: Partial<AppSettings> = {
  video_pipeline_mode: 'direct',
  video_low_latency_mode: true,
  video_thread_queue_size: 16,
  audio_thread_queue_size: 64,
  video_bitrate: '3M',
  video_maxrate: '3M',
  video_bufsize: '1M',
  video_analysis_fps: 5,
  video_analysis_width: 640,
  video_analysis_height: 360,
  video_rtsp_transport: 'tcp',
};

export function ControlPanel({ settings, setSettings, videoDevices, audioDevices, onRefresh, onStart, onStop, dirty, busyAction, errorMessage }: { settings: AppSettings | null; setSettings: (s: AppSettings) => void; videoDevices: Device[]; audioDevices: Device[]; onRefresh: () => void; onStart: () => void; onStop: () => void; dirty: boolean; busyAction: 'refresh' | 'start' | 'stop' | null; errorMessage: string | null }) {
  if (!settings) return <section className="card"><h2>控制面板</h2>加载中...</section>;
  const update = (patch: Partial<AppSettings>) => setSettings({ ...settings, ...patch });
  const selectedAudio = audioDevices.find(d => String(d.id ?? '') === String(settings.audio_device ?? ''));
  const selectedVideo = videoDevices.find(d => String(d.id ?? '') === String(settings.video_device ?? ''));
  const videoFormats = selectedVideo?.formats ?? [];
  const formatLabel = (fourcc?: string | null, label?: string) => label || ({ MJPG: 'MJPEG', H264: 'H.264', YUYV: 'YUYV' }[fourcc ?? ''] ?? fourcc ?? '默认');
  const formatAudioDeviceLabel = (d: Device) => {
    const maxRate = d.max_sample_rate ? `最大 ${d.max_sample_rate} Hz` : d.default_sample_rate ? `默认 ${d.default_sample_rate} Hz` : '采样率未知';
    const maxChannels = d.max_channels ?? d.channels;
    const channelText = maxChannels ? `最大 ${maxChannels} 通道` : '通道未知';
    return `${d.name} (${maxRate}，${channelText})`;
  };
  const updateVideoDevice = (value: string) => {
    const selected = videoDevices.find(d => String(d.id ?? '') === value);
    const formats = selected?.formats ?? [];
    const hasCurrentFormat = settings.video_fourcc ? formats.some(f => f.fourcc === settings.video_fourcc) : true;
    update({ video_device: value, video_fourcc: hasCurrentFormat ? settings.video_fourcc : formats[0]?.fourcc ?? null });
  };
  const updateAudioDevice = (value: string) => {
    const nextDevice = value === '' ? null : Number.isNaN(Number(value)) ? value : Number(value);
    const selected = audioDevices.find(d => String(d.id ?? '') === value);
    update({
      audio_device: nextDevice,
      ...(selected?.max_sample_rate ? { audio_sample_rate: selected.max_sample_rate } : selected?.default_sample_rate ? { audio_sample_rate: selected.default_sample_rate } : {}),
      ...((selected?.max_channels ?? selected?.channels) ? { audio_channels: selected.max_channels ?? selected.channels ?? settings.audio_channels } : {}),
    });
  };
  const applyLowLatencyPreset = () => update(lowLatencyPreset);
  return <section className="card"><h2>控制面板</h2>
    <button type="button" onClick={applyLowLatencyPreset}>应用低延迟推荐配置</button>
    <label className="checkbox"><input type="checkbox" checked={settings.video_low_latency_mode} onChange={e=>update({video_low_latency_mode:e.target.checked})}/>低延迟模式（启用 FFmpeg 低缓冲参数）</label>
    <label>视频设备<select value={settings.video_device} onChange={e=>updateVideoDevice(e.target.value)}>{videoDevices.map(d=><option key={String(d.id)} value={String(d.id)} disabled={!d.available}>{d.name} ({String(d.id)})</option>)}</select></label>
    <label>摄像头编码格式<select value={settings.video_fourcc ?? ''} onChange={e=>update({video_fourcc:e.target.value || null})}><option value="">默认/不指定</option>{videoFormats.map(f=><option key={f.fourcc} value={f.fourcc}>{formatLabel(f.fourcc, f.label)}</option>)}</select></label>
    {selectedVideo && <p className="hint">摄像头支持格式：{videoFormats.length ? videoFormats.map(f=>formatLabel(f.fourcc, f.label)).join(' / ') : '未探测到可用格式'}。{selectedVideo.format_error ? ` 探测提示：${selectedVideo.format_error}` : ''}</p>}
    <label>音频设备<select value={settings.audio_device == null ? '' : String(settings.audio_device)} onChange={e=>updateAudioDevice(e.target.value)}><option value="">默认设备</option>{audioDevices.map(d=><option key={String(d.id)} value={String(d.id ?? '')} disabled={!d.available}>{formatAudioDeviceLabel(d)}</option>)}</select></label>
    {selectedAudio && <p className="hint">当前麦克风能力：最大采样率 {selectedAudio.max_sample_rate ?? '未知'} Hz，最大通道 {selectedAudio.max_channels ?? selectedAudio.channels ?? '未知'}。{selectedAudio.supported_sample_rates?.length ? ` 可用采样率：${selectedAudio.supported_sample_rates.join(' / ')} Hz。` : ''}{selectedAudio.supports_configured_sample_rate === false ? ` 当前采样率不可用：${selectedAudio.sample_rate_error}` : ''}</p>}
    <div className="grid2">
      <label>宽度<input type="number" value={settings.video_width} onChange={e=>update({video_width:Number(e.target.value)})}/></label>
      <label>高度<input type="number" value={settings.video_height} onChange={e=>update({video_height:Number(e.target.value)})}/></label>
      <label>推流 FPS<input type="number" value={settings.video_fps} onChange={e=>update({video_fps:Number(e.target.value)})}/></label>
      <label>OpenCV 分析 FPS<input type="number" min="1" max="120" value={settings.video_analysis_fps} onChange={e=>update({video_analysis_fps:Number(e.target.value)})}/></label>
      <label>视频管线<select value={settings.video_pipeline_mode} onChange={e=>update({video_pipeline_mode:e.target.value})}><option value="direct">FFmpeg 直推 + 前端叠加（低延迟推荐）</option><option value="opencv">OpenCV 处理后推流</option></select></label>
      <label>视频编码器<select value={settings.video_encoder} onChange={e=>update({video_encoder:e.target.value})}><option value="libx264">libx264 (CPU)</option><option value="h264_nvenc">h264_nvenc (NVIDIA)</option></select></label>
      <label>编码器预设<input value={settings.video_encoder_preset ?? ''} placeholder={settings.video_encoder === 'h264_nvenc' ? 'p1' : 'ultrafast'} onChange={e=>update({video_encoder_preset:e.target.value || null})}/></label>
      <label>视频码率<input value={settings.video_bitrate ?? ''} placeholder="例如 3M" onChange={e=>update({video_bitrate:e.target.value || null})}/></label>
      <label>最大码率<input value={settings.video_maxrate ?? ''} placeholder="例如 3M" onChange={e=>update({video_maxrate:e.target.value || null})}/></label>
      <label>VBV 缓冲<input value={settings.video_bufsize ?? ''} placeholder="例如 1M" onChange={e=>update({video_bufsize:e.target.value || null})}/></label>
      <label>视频队列<input type="number" min="1" max="1024" value={settings.video_thread_queue_size} onChange={e=>update({video_thread_queue_size:Number(e.target.value)})}/></label>
      <label>音频队列<input type="number" min="1" max="1024" value={settings.audio_thread_queue_size} onChange={e=>update({audio_thread_queue_size:Number(e.target.value)})}/></label>
      <label>RTSP 传输<select value={settings.video_rtsp_transport} onChange={e=>update({video_rtsp_transport:e.target.value as 'tcp' | 'udp'})}><option value="tcp">TCP（稳定）</option><option value="udp">UDP（可尝试更低延迟）</option></select></label>
      <label>分析宽度<input type="number" value={settings.video_analysis_width ?? ''} placeholder="默认同主画面" onChange={e=>update({video_analysis_width:e.target.value ? Number(e.target.value) : null})}/></label>
      <label>分析高度<input type="number" value={settings.video_analysis_height ?? ''} placeholder="默认同主画面" onChange={e=>update({video_analysis_height:e.target.value ? Number(e.target.value) : null})}/></label>
      <label>音频采样率<input type="number" value={settings.audio_sample_rate} onChange={e=>update({audio_sample_rate:Number(e.target.value)})}/></label>
      <label>音频通道数<input type="number" min="1" max={selectedAudio?.max_channels ?? 8} value={settings.audio_channels} onChange={e=>update({audio_channels:Number(e.target.value)})}/></label>
      <label>音频块大小<input type="number" value={settings.audio_block_size} onChange={e=>update({audio_block_size:Number(e.target.value)})}/></label>
      <label>播放增益<input type="number" min="0.1" max="20" step="0.1" value={settings.audio_playback_gain} onChange={e=>update({audio_playback_gain:Number(e.target.value)})}/></label>
      <label>音频指标间隔 ms<input type="number" min="20" max="1000" value={settings.audio_metrics_interval_ms} onChange={e=>update({audio_metrics_interval_ms:Number(e.target.value)})}/></label>
      <label>视频算法<select value={settings.video_algorithm} onChange={e=>update({video_algorithm:e.target.value})}><option value="dummy">dummy</option><option value="motion">motion</option></select></label>
    </div>
    {settings.video_pipeline_mode !== 'direct' && <p className="warn">低延迟监看建议使用 direct 管线；opencv 会先处理再推流。</p>}
    {dirty && <p className="warn">设置已修改，点击启动管线后会应用当前设置。</p>}
    {errorMessage && <p className="error">{errorMessage}</p>}
    <div className="buttons"><button onClick={onRefresh} disabled={busyAction !== null}>{busyAction === 'refresh' ? '刷新中...' : '刷新设备'}</button><button onClick={onStart} disabled={busyAction !== null}>{busyAction === 'start' ? '启动中...' : '启动管线'}</button><button onClick={onStop} disabled={busyAction !== null}>{busyAction === 'stop' ? '停止中...' : '停止管线'}</button></div>
  </section>;
}
