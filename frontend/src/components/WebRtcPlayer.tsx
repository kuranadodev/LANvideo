import { useEffect, useRef, useState } from 'react';
import type { WebRtcStats } from '../types/messages';

const MAX_STREAM_RETRIES = 8;
const STREAM_RETRY_DELAY_MS = 1000;

function whepUrl(url: string) {
  const parsed = new URL(url, window.location.href);
  if (!parsed.pathname.endsWith('/whep')) parsed.pathname = `${parsed.pathname.replace(/\/$/, '')}/whep`;
  return parsed.toString();
}

function isStreamUnavailable(status: number, body: string) {
  return status === 404 && body.toLowerCase().includes('no stream is available');
}

export function WebRtcPlayer({ url, onStats }: { url: string; onStats: (stats: WebRtcStats | null) => void }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [statusText, setStatusText] = useState('正在连接视频流…');

  useEffect(() => {
    if (!url) return;
    let closed = false;
    let statsTimer = 0;
    let retryTimer = 0;
    let pc: RTCPeerConnection | null = null;

    const closePeer = () => {
      pc?.getSenders().forEach(sender => sender.track?.stop());
      pc?.getReceivers().forEach(receiver => receiver.track?.stop());
      pc?.close();
      pc = null;
    };

    const stop = () => {
      closed = true;
      window.clearInterval(statsTimer);
      window.clearTimeout(retryTimer);
      onStats(null);
      if (videoRef.current) videoRef.current.srcObject = null;
      closePeer();
    };

    const collectStats = async () => {
      if (!pc) return;
      const report = await pc.getStats();
      let inbound: any;
      let pair: any;
      let remoteCandidate: any;
      let localCandidate: any;
      report.forEach(item => {
        if (item.type === 'inbound-rtp' && item.kind === 'video') inbound = item;
        if (item.type === 'candidate-pair' && item.state === 'succeeded' && item.selected) pair = item;
      });
      if (pair) {
        remoteCandidate = report.get(pair.remoteCandidateId);
        localCandidate = report.get(pair.localCandidateId);
      }
      onStats({
        rttMs: pair?.currentRoundTripTime != null ? pair.currentRoundTripTime * 1000 : undefined,
        jitterMs: inbound?.jitter != null ? inbound.jitter * 1000 : undefined,
        framesDecoded: inbound?.framesDecoded,
        framesDropped: inbound?.framesDropped,
        bytesReceived: inbound?.bytesReceived,
        candidatePair: pair && localCandidate && remoteCandidate ? `${localCandidate.candidateType}/${remoteCandidate.candidateType}` : undefined,
      });
    };

    const start = async (attempt = 0) => {
      closePeer();
      if (videoRef.current) videoRef.current.srcObject = null;
      pc = new RTCPeerConnection({ iceServers: [] });

      try {
        setError(null);
        setStatusText(attempt === 0 ? '正在连接视频流…' : `等待视频流发布…（第 ${attempt + 1} 次尝试）`);
        pc.addTransceiver('video', { direction: 'recvonly' });
        pc.addTransceiver('audio', { direction: 'recvonly' });
        pc.ontrack = event => {
          if (closed || !videoRef.current) return;
          videoRef.current.srcObject = event.streams[0];
          setStatusText('');
        };
        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);
        await new Promise<void>(resolve => {
          if (!pc || pc.iceGatheringState === 'complete') return resolve();
          const timeout = window.setTimeout(resolve, 1500);
          pc.addEventListener('icegatheringstatechange', () => {
            if (pc?.iceGatheringState === 'complete') {
              window.clearTimeout(timeout);
              resolve();
            }
          });
        });
        const res = await fetch(whepUrl(url), { method: 'POST', headers: { 'Content-Type': 'application/sdp' }, body: pc.localDescription?.sdp ?? offer.sdp ?? '' });
        const body = await res.text();
        if (!res.ok) {
          if (isStreamUnavailable(res.status, body) && attempt < MAX_STREAM_RETRIES) {
            closePeer();
            retryTimer = window.setTimeout(() => start(attempt + 1), STREAM_RETRY_DELAY_MS);
            return;
          }
          throw new Error(`WHEP ${res.status}: ${body}`);
        }
        await pc.setRemoteDescription({ type: 'answer', sdp: body });
        statsTimer = window.setInterval(() => collectStats().catch(() => {}), 1000);
      } catch (err) {
        if (!closed) {
          setStatusText('');
          setError(err instanceof Error ? err.message : String(err));
        }
      }
    };

    start();
    return stop;
  }, [url, onStats]);

  return <><video ref={videoRef} className="video-layer" autoPlay playsInline muted controls={false} />{statusText && <div className="video-status">{statusText}</div>}{error && <div className="video-error">WebRTC 播放失败：{error}</div>}</>;
}
