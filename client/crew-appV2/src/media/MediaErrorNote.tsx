import { CameraOff, MicOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { MediaError } from "./useMicRecorder";

const copy: Record<Exclude<MediaError, null>, string> = {
  denied: "Access was blocked. Allow it in your browser settings, then try again.",
  unavailable: "We couldn't find a working device on this phone.",
  insecure: "This needs a secure (https) connection to the ship server.",
};

export function MediaErrorNote({ error, kind, onRetry, fallback }: { error: MediaError; kind: "mic" | "camera"; onRetry: () => void; fallback?: string }) {
  if (!error) return null;
  const Icon = kind === "mic" ? MicOff : CameraOff;
  return (
    <div role="status" className="flex items-start gap-3 rounded-xl bg-warn-soft p-3 text-sm text-foreground">
      <Icon className="mt-0.5 size-4 shrink-0 text-warn" aria-hidden />
      <div className="flex-1">
        <p>{copy[error]}</p>
        {fallback && <p className="mt-1 text-muted-foreground">{fallback}</p>}
      </div>
      <Button size="sm" variant="ghost" onClick={onRetry}>Try again</Button>
    </div>
  );
}
