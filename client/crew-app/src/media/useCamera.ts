import { useCallback, useEffect, useRef, useState } from "react";
import { classifyMediaError, type MediaError } from "./useMicRecorder";

/** Live camera preview with front/back switching and JPEG capture. Stops tracks when inactive. */
export function useCamera(active: boolean) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const [facing, setFacing] = useState<"environment" | "user">("environment");
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<MediaError>(null);
  const [attempt, setAttempt] = useState(0);
  const [canSwitch, setCanSwitch] = useState(false);

  const stopTracks = () => { stream.current?.getTracks().forEach((t) => t.stop()); stream.current = null; };

  useEffect(() => {
    if (!active) { stopTracks(); setReady(false); return; }
    let cancelled = false;
    (async () => {
      setError(null);
      setReady(false);
      if (!navigator.mediaDevices?.getUserMedia) { setError(classifyMediaError(null)); return; }
      try {
        stopTracks();
        const s = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: facing }, width: { ideal: 1920 }, height: { ideal: 1080 } }, audio: false });
        if (cancelled) { s.getTracks().forEach((t) => t.stop()); return; }
        stream.current = s;
        if (videoRef.current) { videoRef.current.srcObject = s; await videoRef.current.play().catch(() => {}); }
        setReady(true);
        const devs = await navigator.mediaDevices.enumerateDevices();
        setCanSwitch(devs.filter((d) => d.kind === "videoinput").length > 1);
      } catch (e) {
        if (!cancelled) setError(classifyMediaError(e));
      }
    })();
    return () => { cancelled = true; stopTracks(); };
  }, [active, facing, attempt]);

  const capture = useCallback(async (): Promise<Blob | null> => {
    const v = videoRef.current;
    if (!v || !v.videoWidth) return null;
    const c = document.createElement("canvas");
    c.width = v.videoWidth;
    c.height = v.videoHeight;
    const g = c.getContext("2d")!;
    if (facing === "user") { g.translate(c.width, 0); g.scale(-1, 1); }
    g.drawImage(v, 0, 0);
    return new Promise((res) => c.toBlob((b) => res(b), "image/jpeg", 0.85));
  }, [facing]);

  return {
    videoRef, ready, error, facing, canSwitch, capture,
    flip: () => setFacing((f) => (f === "user" ? "environment" : "user")),
    retry: () => setAttempt((a) => a + 1),
  };
}
