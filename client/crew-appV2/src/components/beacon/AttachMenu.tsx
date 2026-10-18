import { useRef, useState } from "react";
import { Camera, FileImage, Images, Paperclip } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { CameraSheet } from "@/media/CameraSheet";
import { cn } from "@/lib/utils";

/** Paperclip button: live camera, photo library or files. */
export function AttachMenu({ remaining, onAdd, defaultOpen = false }: { remaining: number; onAdd: (b: Blob[]) => void; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  const [cam, setCam] = useState(false);
  const lib = useRef<HTMLInputElement>(null);
  const files = useRef<HTMLInputElement>(null);
  const full = remaining <= 0;
  const opts = [
    { label: "Take photo", sub: "Live camera", icon: Camera, cls: "bg-coral-soft text-coral", run: () => setCam(true) },
    { label: "Photo library", sub: "Choose from gallery", icon: Images, cls: "bg-lavender-soft text-lavender", run: () => lib.current?.click() },
    { label: "Files", sub: "Any image file", icon: FileImage, cls: "bg-primary-soft text-primary", run: () => files.current?.click() },
  ];
  const pick = (e: React.ChangeEvent<HTMLInputElement>) => { onAdd([...(e.target.files ?? [])].slice(0, remaining)); e.target.value = ""; };

  return (
    <>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <button type="button" disabled={full} aria-label="Attach photos" className={cn("tap grid shrink-0 place-items-center rounded-full text-muted-foreground transition hover:bg-muted disabled:opacity-40", open && "bg-muted text-foreground")}>
            <Paperclip className="size-5" />
          </button>
        </PopoverTrigger>
        <PopoverContent side="top" align="start" className="w-64 rounded-3xl p-2">
          <p className="px-3 pb-1 pt-2 text-xs text-muted-foreground">Add up to {remaining} more</p>
          {opts.map((o) => (
            <button key={o.label} type="button" onClick={() => { setOpen(false); o.run(); }} className="flex w-full items-center gap-3 rounded-2xl p-2.5 text-left hover:bg-muted">
              <span className={cn("grid size-10 place-items-center rounded-xl", o.cls)}><o.icon className="size-5" /></span>
              <span><span className="block text-sm font-semibold">{o.label}</span><span className="block text-xs text-muted-foreground">{o.sub}</span></span>
            </button>
          ))}
        </PopoverContent>
      </Popover>
      <input ref={lib} type="file" accept="image/*" multiple hidden onChange={pick} />
      <input ref={files} type="file" accept="image/*,.heic,.heif" multiple hidden onChange={pick} />
      <CameraSheet open={cam} onOpenChange={setCam} remaining={remaining} onCapture={(b) => onAdd([b])} />
    </>
  );
}
