import type { WebRtcStats } from '../types/messages';

export function MetricsPanel({ status, metrics, audio, webRtcStats }: { status: any; metrics: any; audio: any; webRtcStats?: WebRtcStats | null }) {
  const capabilities = status?.system?.capabilities;
  const ffmpeg = capabilities?.ffmpeg;
  const opencv = capabilities?.opencv;
  const nvidia = capabilities?.nvidia_smi;
  const gpuNames = nvidia?.gpus?.map?.((gpu: any) => gpu.name).join(', ') || '-';
  const video = status?.video;
  const warnings = [
    video?.pipeline_mode && video.pipeline_mode !== 'direct' ? '低延迟监看建议使用 direct 管线。' : null,
    video?.thread_queue_size && video.thread_queue_size > 64 ? '视频队列较大，可能积压旧帧。' : null,
    !video?.bitrate || !video?.bufsize ? '建议设置码率和 VBV 缓冲以减少播放端缓冲。' : null,
  ].filter(Boolean);
  return <section className="card"><h2>状态/性能</h2>
    <p>管线状态：{status?.state ?? '未知'}</p>
    <p>视频：{video?.running ? '运行中' : '停止'} {video?.error && <span className="error">{video.error}</span>}</p>
    <p>音频：{status?.audio?.running ? '运行中' : '停止'} {status?.audio?.error && <span className="error">{status.audio.error}</span>}</p>
    <p>视频管线：{video?.pipeline_mode === 'direct' ? 'FFmpeg 直推 + 前端叠加' : video?.pipeline_mode === 'opencv' ? 'OpenCV 处理后推流' : '-'}</p>
    <p>低延迟模式：{video?.low_latency_mode ? '开启' : '关闭'}；RTSP：{video?.rtsp_transport ?? '-'}</p>
    <p>视频编码器：{video?.encoder ?? '-'}；码率：{video?.bitrate ?? '-'} / max {video?.maxrate ?? '-'} / buf {video?.bufsize ?? '-'}</p>
    <p>队列：视频 {video?.thread_queue_size ?? '-'} / 音频 {status?.audio?.thread_queue_size ?? '-'}</p>
    <p>分析分辨率：{video?.analysis_width ?? video?.width ?? '-'}x{video?.analysis_height ?? video?.height ?? '-'}</p>
    {warnings.length > 0 && <ul className="warn-list">{warnings.map((warning, index)=><li key={index}>{warning}</li>)}</ul>}
    <p>NVENC：{ffmpeg?.has_h264_nvenc === true ? '可用' : ffmpeg?.has_h264_nvenc === false ? '不可用' : '-'}</p>
    <p>OpenCV CUDA：{opencv?.cuda_available ? `可用（${opencv.cuda_device_count} 个设备）` : opencv ? '不可用' : '-'}</p>
    <p>NVIDIA GPU：{gpuNames}</p>
    <p>推流 FPS：{metrics?.fps?.toFixed?.(1) ?? video?.fps ?? '-'}</p>
    <p>OpenCV 分析 FPS：{metrics?.analysis_fps?.toFixed?.(1) ?? video?.actual_fps?.toFixed?.(1) ?? '-'}</p>
    <p>算法耗时：{metrics?.algorithm_ms?.toFixed?.(1) ?? '-'} ms</p>
    <p>WebRTC RTT：{webRtcStats?.rttMs?.toFixed?.(1) ?? '-'} ms；Jitter：{webRtcStats?.jitterMs?.toFixed?.(1) ?? '-'} ms</p>
    <p>WebRTC 帧：decoded {webRtcStats?.framesDecoded ?? '-'} / dropped {webRtcStats?.framesDropped ?? '-'}；候选：{webRtcStats?.candidatePair ?? '-'}</p>
    <p>RMS：{audio?.rms?.toFixed?.(4) ?? '-'}</p><p>Peak：{audio?.peak?.toFixed?.(4) ?? '-'}</p><p>CPU：{status?.system?.cpu_percent ?? '-'}%</p><p>内存：{status?.system?.memory_percent ?? '-'}%</p>
  </section>;
}
