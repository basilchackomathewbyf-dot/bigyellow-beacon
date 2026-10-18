import { useCallback, useEffect, useRef, useState } from "react";
import { MAX_RECORDING_SECONDS } from "@/lib/rules";

export type MediaError = "denied" | "unavailable" | "insecure" | null;

const pickMime = () => {
  if (typeof MediaRecorder === "undefined") return "";
  return ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg"].find((m) => MediaRecorder.isTypeSupported(m)) ?? "";
};

export const classifyMediaError = (e: unknown): MediaError => {
  if (typeof window !== "undefined" && !window.isSecureContext) return "insecure";
  const name = (e as DOMException)?.name;
  if (name === "NotAllowedError" || name === "SecurityError") return "denied";
  return "unavailable";
};

/** Live microphone recorder with level meter and a hard max length. */
export function useMicRecorder(maxSeconds = MAX_RECORDING_SECONDS) {
  const [recording, setRecording] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [levels, setLevels] = useState<number[]>([]);
  const [blob, setBlob] = useState<Blob | null>(null);
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState<MediaError>(null);

  const rec = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const ctx = useRef<AudioContext | null>(null);
  const raf = useRef<number>(0);
  const started = useRef(0);
  const chunks = useRef<BlobPart[]>([]);

  const cleanup = useCallback(() => {
    cancelAnimationFrame(raf.current);
    stream.current?.getTracks().forEach((t) => t.stop());
    stream.current = null;
    void ctx.current?.close().catch(() => {});
    ctx.current = null;
  }, []);

  const stop = useCallback(() => {
    if (rec.current && rec.current.state !== "inactive") rec.current.stop();
    setRecording(false);
  }, []);

  const start = useCallback(async () => {
    setError(null);
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") { setError(classifyMediaError(null)); return; }
    try {
      const s = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
      stream.current = s;
      const mime = pickMime();
      const r = new MediaRecorder(s, mime ? { mimeType: mime } : undefined);
      chunks.current = [];
      r.ondataavailable = (e) => { if (e.data.size) chunks.current.push(e.data); };
      r.onstop = () => {
        const b = new Blob(chunks.current, { type: r.mimeType || "audio/webm" });
        setBlob(b);
        setUrl((old) => { if (old) URL.revokeObjectURL(old); return URL.createObjectURL(b); });
        cleanup();
      };
      rec.current = r;

      const AC = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const ac = new AC();
      ctx.current = ac;
      const an = ac.createAnalyser();
      an.fftSize = 256;
      ac.createMediaStreamSource(s).connect(an);
      const data = new Uint8Array(an.frequencyBinCount);

      r.start(250);
      started.current = performance.now();
      setRecording(true);
      setElapsed(0);
      setLevels([]);
      let lastPush = 0;
      const tick = (t: number) => {
        an.getByteTimeDomainData(data);
        let sum = 0;
        for (const v of data) sum += ((v - 128) / 128) ** 2;
        const rms = Math.min(1, Math.sqrt(sum / data.length) * 3.2);
        if (t - lastPush > 70) { setLevels((l) => [...l.slice(-47), rms]); lastPush = t; }
        const secs = (performance.now() - started.current) / 1000;
        setElapsed(secs);
        if (secs >= maxSeconds) { r.state !== "inactive" && r.stop(); setRecording(false); return; }
        raf.current = requestAnimationFrame(tick);
      };
      raf.current = requestAnimationFrame(tick);
    } catch (e) {
      cleanup();
      setError(classifyMediaError(e));
    }
  }, [cleanup, maxSeconds]);

  const discard = useCallback(() => {
    setBlob(null);
    setUrl((old) => { if (old) URL.revokeObjectURL(old); return null; });
    setElapsed(0);
    setLevels([]);
  }, []);

  useEffect(() => () => { rec.current?.state === "recording" && rec.current.stop(); cleanup(); }, [cleanup]);

  return { recording, elapsed, levels, blob, url, error, start, stop, discard, maxSeconds };
}
