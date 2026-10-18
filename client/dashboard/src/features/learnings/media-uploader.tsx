import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Film, ImagePlus, Info, Star, Trash2, UploadCloud } from "lucide-react";
import type { MediaItem } from "@/api/types";
import { useUploadLearningMedia } from "@/hooks/use-content";
import { SHIP_BUDGET_BYTES, canAddMedia, classifyFile, estimateDeliveryBytes } from "@/lib/rules";
import { bytes } from "@/lib/format";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { toast } from "sonner";

function readVideoDuration(file: File): Promise<number> {
  return new Promise((resolve, reject) => {
    const v = document.createElement("video");
    v.preload = "metadata";
    v.onloadedmetadata = () => {
      URL.revokeObjectURL(v.src);
      resolve(v.duration);
    };
    v.onerror = () => reject(new Error("Could not read video"));
    v.src = URL.createObjectURL(file);
  });
}

export function MediaUploader({
  value,
  onChange,
  ticketPhotos,
}: {
  value: MediaItem[];
  onChange: (m: MediaItem[]) => void;
  ticketPhotos: string[];
}) {
  const { t } = useTranslation();
  const input = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);
  const [notes, setNotes] = useState<string[]>([]);
  const upload = useUploadLearningMedia();
  const est = estimateDeliveryBytes(value);
  const over = est > SHIP_BUDGET_BYTES;

  async function handle(files: FileList | null) {
    if (!files) return;
    let list = [...value];
    const newNotes: string[] = [];
    for (const f of Array.from(files)) {
      const duration = f.type.startsWith("video/") ? await readVideoDuration(f).catch(() => undefined) : undefined;
      const res = classifyFile(f, duration);
      if (!res.ok) {
        toast.error(res.error);
        continue;
      }
      if (!canAddMedia(list, res.kind)) {
        toast.error(t("learn.tooMany"));
        continue;
      }
      if (res.note === "resize") newNotes.push(t("learn.resizeNote"));
      if (res.note === "gif_to_video") newNotes.push(t("learn.gifNote"));
      try {
        const item = await upload.mutateAsync({ file: f, meta: { kind: res.kind, bytes: f.size, duration_s: duration, primary: list.length === 0 } });
        list = [...list, item];
      } catch {
        toast.error(t("common.error"));
      }
    }
    setNotes([...new Set(newNotes)]);
    onChange(list);
  }

  const addTicketPhoto = (url: string) => {
    if (!canAddMedia(value, "image")) {
      toast.error(t("learn.tooMany"));
      return;
    }
    onChange([...value, { id: `tp${Date.now()}`, kind: "image", url, bytes: 400_000, primary: value.length === 0 }]);
  };
  const remove = (id: string) => {
    const rest = value.filter((m) => m.id !== id);
    if (rest.length && !rest.some((m) => m.primary)) rest[0] = { ...rest[0], primary: true };
    onChange(rest);
  };
  const makePrimary = (id: string) => onChange(value.map((m) => ({ ...m, primary: m.id === id })));

  return (
    <div className="space-y-3">
      <div
        role="button"
        tabIndex={0}
        aria-disabled={upload.isPending}
        onClick={() => { if (!upload.isPending) input.current?.click(); }}
        onKeyDown={(e) => e.key === "Enter" && input.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          handle(e.dataTransfer.files);
        }}
        className={cn("flex cursor-pointer flex-col items-center gap-2 rounded-xl border-2 border-dashed p-6 text-center transition", drag ? "border-primary bg-primary-soft" : "hover:border-primary/50")}
      >
        <UploadCloud className="size-7 text-primary" aria-hidden />
        <div className="text-sm font-medium">{t("learn.dropHere")}</div>
        <div className="text-xs text-muted-foreground">{t("learn.mediaRules")}</div>
        <input ref={input} type="file" hidden multiple disabled={upload.isPending} accept="image/jpeg,image/png,image/webp,image/gif,video/*" onChange={(e) => { handle(e.target.files); e.target.value = ""; }} />
      </div>

      {notes.map((n) => (
        <p key={n} className="flex items-center gap-1.5 text-xs text-seaglass-strong"><Info className="size-3.5" aria-hidden />{n}</p>
      ))}

      {ticketPhotos.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {ticketPhotos.map((p) => (
            <Button key={p} type="button" variant="outline" size="sm" onClick={() => addTicketPhoto(p)}>
              <ImagePlus /> {t("learn.useTicketPhoto")}
            </Button>
          ))}
        </div>
      )}

      {value.length > 0 && (
        <div className="grid grid-cols-3 gap-2">
          {value.map((m) => (
            <div key={m.id} className={cn("group relative overflow-hidden rounded-lg border", m.primary && "ring-2 ring-primary")}>
              {m.kind === "image" ? <img src={m.url} alt="" className="aspect-video w-full object-cover" /> : <div className="grid aspect-video place-items-center bg-muted"><Film className="size-6 text-muted-foreground" aria-hidden /></div>}
              <div className="flex items-center justify-between bg-card px-2 py-1 text-[11px] text-muted-foreground">
                <span>{m.kind}{m.duration_s ? ` · ${m.duration_s.toFixed(1)}s` : ""}</span>
                <span className="flex gap-1">
                  {!m.primary && (
                    <button type="button" aria-label={t("learn.primary")} onClick={() => makePrimary(m.id)} className="hover:text-primary"><Star className="size-3.5" /></button>
                  )}
                  <button type="button" aria-label={t("learn.remove")} onClick={() => remove(m.id)} className="hover:text-destructive"><Trash2 className="size-3.5" /></button>
                </span>
              </div>
              {m.primary && <span className="absolute left-1.5 top-1.5 rounded bg-primary px-1.5 text-[10px] font-semibold text-primary-foreground">{t("learn.primary")}</span>}
            </div>
          ))}
        </div>
      )}

      <div>
        <div className="mb-1 flex justify-between text-xs">
          <span className="text-muted-foreground">{t("learn.budget")}</span>
          <span className={cn("font-medium tabular-nums", over && "text-destructive")}>{t("learn.budgetOf", { size: bytes(est) })}</span>
        </div>
        <Progress value={Math.min(100, (est / SHIP_BUDGET_BYTES) * 100)} className={cn("h-1.5", over && "[&>div]:bg-destructive")} />
        {over && <p className="mt-1 text-xs text-destructive">{t("learn.overBudget")}</p>}
      </div>
    </div>
  );
}
