import { useState } from "react";
import { Check, RefreshCw, SwitchCamera, X } from "lucide-react";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { useCamera } from "./useCamera";
import { MediaErrorNote } from "./MediaErrorNote";

/** Full-screen live camera. Calls onCapture for each shot; closes at `remaining` = 0. */
export function CameraSheet({ open, onOpenChange, onCapture, remaining = 1 }: {
  open: boolean; onOpenChange: (o: boolean) => void; onCapture: (b: Blob) => void; remaining?: number;
}) {
  const cam = useCamera(open);
  const [flash, setFlash] = useState(false);
  const [shots, setShots] = useState(0);
  const left = remaining - shots;

  const shoot = async () => {
    const b = await cam.capture();
    if (!b) return;
    setFlash(true);
    setTimeout(() => setFlash(false), 120);
    onCapture(b);
    const n = shots + 1;
    setShots(n);
    if (n >= remaining) close();
  };
  const close = () => { setShots(0); onOpenChange(false); };

  return (
    <Dialog open={open} onOpenChange={(o) => (o ? onOpenChange(o) : close())}>
      <DialogContent className="h-[100dvh] max-w-none gap-0 overflow-hidden rounded-none border-0 bg-ink p-0 sm:h-[85vh] sm:max-w-xl sm:rounded-3xl [&>button]:hidden">
        <DialogTitle className="sr-only">Camera</DialogTitle>
        <div className="relative flex h-full flex-col">
          <video
            ref={cam.videoRef}
            playsInline
            muted
            className={`absolute inset-0 size-full object-cover ${cam.facing === "user" ? "-scale-x-100" : ""}`}
          />
          {flash && <div className="absolute inset-0 bg-ink-foreground/70" />}
          <div className="relative z-10 flex items-center justify-between p-4">
            <button aria-label="Close camera" onClick={close} className="tap grid place-items-center rounded-full bg-ink/50 text-ink-foreground backdrop-blur">
              <X className="size-5" />
            </button>
            <span className="rounded-full bg-ink/50 px-3 py-1 text-xs font-medium text-ink-foreground backdrop-blur">
              {left} left
            </span>
          </div>
          <div className="relative z-10 flex flex-1 items-center justify-center p-6">
            {!cam.ready && !cam.error && (
              <RefreshCw className="size-6 animate-spin text-ink-foreground/70" aria-label="Starting camera" />
            )}
            {cam.error && (
              <div className="w-full max-w-sm rounded-2xl bg-card p-2">
                <MediaErrorNote error={cam.error} kind="camera" onRetry={cam.retry} fallback="You can still add photos from the gallery." />
              </div>
            )}
          </div>
          <div className="relative z-10 flex items-center justify-around pb-[max(env(safe-area-inset-bottom),2rem)] pt-4">
            <span className="size-12" />
            <button
              aria-label="Take photo"
              disabled={!cam.ready}
              onClick={shoot}
              className="grid size-20 place-items-center rounded-full border-4 border-ink-foreground/90 transition active:scale-95 disabled:opacity-40"
            >
              <span className="size-16 rounded-full bg-ink-foreground" />
            </button>
            {cam.canSwitch ? (
              <button aria-label="Switch camera" onClick={cam.flip} className="tap grid size-12 place-items-center rounded-full bg-ink/50 text-ink-foreground backdrop-blur">
                <SwitchCamera className="size-5" />
              </button>
            ) : shots > 0 ? (
              <button aria-label="Done" onClick={close} className="tap grid size-12 place-items-center rounded-full bg-secondary text-secondary-foreground">
                <Check className="size-5" />
              </button>
            ) : <span className="size-12" />}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
