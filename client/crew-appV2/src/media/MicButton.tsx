import { Mic, Square } from "lucide-react";
import { useMicRecorder } from "./useMicRecorder";
import { MediaErrorNote } from "./MediaErrorNote";
import { useEffect } from "react";

/** Compact tap-to-toggle mic for chat. Emits the recorded blob on stop. */
export function MicButton({ onRecorded }: { onRecorded: (b: Blob) => void }) {
  const mic = useMicRecorder(30);
  useEffect(() => { if (mic.blob) { onRecorded(mic.blob); mic.discard(); } }, [mic.blob]); // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <>
      <button
        type="button"
        aria-label={mic.recording ? "Stop recording" : "Record voice reply"}
        onClick={() => (mic.recording ? mic.stop() : mic.start())}
        className={`tap relative grid shrink-0 place-items-center rounded-full ${mic.recording ? "bg-destructive text-destructive-foreground" : "bg-primary-soft text-primary"}`}
      >
        {mic.recording && <span className="pulse-ring absolute inset-0 rounded-full bg-destructive" />}
        {mic.recording ? <Square className="relative size-4" /> : <Mic className="size-5" />}
      </button>
      {mic.error && <div className="absolute inset-x-3 -top-20"><MediaErrorNote error={mic.error} kind="mic" onRetry={mic.start} fallback="Type your reply instead." /></div>}
    </>
  );
}
