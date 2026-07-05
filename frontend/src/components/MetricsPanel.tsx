export function MetricsPanel({ status, metrics, audio }: { status: any; metrics: any; audio: any }) {
  const capabilities = status?.system?.capabilities;
  const ffmpeg = capabilities?.ffmpeg;
  const opencv = capabilities?.opencv;
  const nvidia = capabilities?.nvidia_smi;
  const gpuNames = nvidia?.gpus?.map?.((gpu: any) => gpu.name).join(', ') || '-';
  return <section className="card"><h2>状态/性能</h2><p>管线状态：{status?.state ?? '未知'}</p><p>视频：{status?.video?.running ? '运行中' : '停止'} {status?.video?.error && <span className="error">{status.video.error}</span>}</p><p>音频：{status?.audio?.running ? '运行中' : '停止'} {status?.audio?.error && <span className="error">{status.audio.error}</span>}</p><p>视频管线：{status?.video?.pipeline_mode === 'direct' ? 'FFmpeg 直推 + 前端叠加' : status?.video?.pipeline_mode === 'opencv' ? 'OpenCV 处理后推流' : '-'}</p><p>视频编码器：{status?.video?.encoder ?? '-'}</p><p>NVENC：{ffmpeg?.has_h264_nvenc === true ? '可用' : ffmpeg?.has_h264_nvenc === false ? '不可用' : '-'}</p><p>OpenCV CUDA：{opencv?.cuda_available ? `可用（${opencv.cuda_device_count} 个设备）` : opencv ? '不可用' : '-'}</p><p>NVIDIA GPU：{gpuNames}</p><p>推流 FPS：{metrics?.fps?.toFixed?.(1) ?? status?.video?.fps ?? '-'}</p><p>OpenCV 分析 FPS：{metrics?.analysis_fps?.toFixed?.(1) ?? status?.video?.actual_fps?.toFixed?.(1) ?? '-'}</p><p>算法耗时：{metrics?.algorithm_ms?.toFixed?.(1) ?? '-'} ms</p><p>RMS：{audio?.rms?.toFixed?.(4) ?? '-'}</p><p>Peak：{audio?.peak?.toFixed?.(4) ?? '-'}</p><p>CPU：{status?.system?.cpu_percent ?? '-'}%</p><p>内存：{status?.system?.memory_percent ?? '-'}%</p></section>;
}
