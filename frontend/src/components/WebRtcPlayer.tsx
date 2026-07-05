import { useEffect, useRef, useState } from 'react';
import type { WebRtcStats } from '../types/messages';

function whepUrl(url: string) {
  const parsed = new URL(url, window.location.href);
  if (!parsed.pathname.endsWith('/whep')) parsed.pathname = `${parsed.pathname.replace(/\/$/, '')}/whep`;
  return parsed.toString();
}

export function WebRtcPlayer({ url, onStats }: { url: string; onStats: (stats: WebRtcStats | null) => void }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!url) return;
    let closed = false;
    let pc: RTCPeerConnection | null = new RTCPeerConnection({ iceServers: [] });
    let statsTimer = 0;

    const stop = () => {
      closed = true;
      window.clearInterval(statsTimer);
      onStats(null);
      if (videoRef.current) videoRef.current.srcObject = null;
      pc?.getSenders().forEach(sender => sender.track?.stop());
      pc?.getReceivers().forEach(receiver => receiver.track?.stop());
      pc?.close();
      pc = null;
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

    const start = async () => {
      try {
        setError(null);
        pc!.addTransceiver('video', { direction: 'recvonly' });
        pc!.addTransceiver('audio', { direction: 'recvonly' });
        pc!.ontrack = event => {
          if (closed || !videoRef.current) return;
          videoRef.current.srcObject = event.streams[0];
        };
        const offer = await pc!.createOffer();
        await pc!.setLocalDescription(offer);
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
        const res = await fetch(whepUrl(url), { method: 'POST', headers: { 'Content-Type': 'application/sdp' }, body: pc!.localDescription?.sdp ?? offer.sdp ?? '' });
        if (!res.ok) throw new Error(`WHEP ${res.status}: ${await res.text()}`);
        await pc!.setRemoteDescription({ type: 'answer', sdp: await res.text() });
        statsTimer = window.setInterval(() => collectStats().catch(() => {}), 1000);
      } catch (err) {
        if (!closed) setError(err instanceof Error ? err.message : String(err));
      }
    };

    start();
    return stop;
  }, [url, onStats]);

  return <><video ref={videoRef} className="video-layer" autoPlay playsInline muted controls={false} />{error && <div className="video-error">WebRTC 播放失败：{error}</div>}</>;
}
