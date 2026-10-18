import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { z } from "zod";
import { Camera, Check, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useAckTicket, useAddAction, useMasterTickets } from "@/hooks/queries";
import { RANKS, timeAgo } from "@/lib/labels";
import type { Ticket } from "@/api/types";
import { CameraSheet } from "@/media/CameraSheet";
import { Thread } from "@/components/beacon/Thread";
import { ListSkeleton, PageHeader, Section, SeverityPill, ShoreChip, severityBar } from "@/components/beacon/bits";
import { TicketBody } from "@/components/beacon/TicketBody";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/_app/master/board")({
  validateSearch: z.object({ t: z.string().optional() }),
  head: () => ({ meta: [{ title: "Near-misses — Beacon" }, { name: "description", content: "All near-miss reports on board." }, { property: "og:title", content: "Near-misses — Beacon" }, { property: "og:description", content: "Near-miss board for the Master." }] }),
  component: Board,
});

interface ColumnDef {
  id: "NEW" | "ACKNOWLEDGED" | "RESOLVED_BY_SHORE";
  label: string;
  match: (t: Ticket) => boolean;
}

const isResolvedByShore = (t: Ticket) =>
  t.shore_status === "CLOSED" ||
  (t.shore_status as string) === "RESOLVED" ||
  (t.shore_status as string) === "RESOLVED_BY_SHORE" ||
  t.onboard_status === "RESOLVED_ON_BOARD";

const COLS: ColumnDef[] = [
  {
    id: "NEW",
    label: "NEW",
    match: (t) =>
      !isResolvedByShore(t) &&
      (t.onboard_status === "SUBMITTED" || (t.onboard_status as string) === "NEW"),
  },
  {
    id: "ACKNOWLEDGED",
    label: "ACKNOWLEDGED",
    match: (t) =>
      !isResolvedByShore(t) &&
      (t.onboard_status === "ACKNOWLEDGED" ||
        t.onboard_status === "ACTION_IN_PROGRESS" ||
        (t.onboard_status as string) === "ACTION_ASSIGNED" ||
        (t.onboard_status as string) === "ACTIONED"),
  },
  {
    id: "RESOLVED_BY_SHORE",
    label: "RESOLVED BY SHORE",
    match: isResolvedByShore,
  },
];

function Card({ t, onOpen }: { t: Ticket; onOpen: () => void }) {
  return (
    <button onClick={onOpen} className="surface relative w-full overflow-hidden p-4 pl-5 text-left transition hover:shadow-lift">
      <span className={cn("absolute inset-y-0 left-0 w-1", severityBar(t.severity))} />
      <div className="flex items-center gap-2"><SeverityPill s={t.severity} withLabel={false} /><span className="ml-auto text-xs text-muted-foreground">{timeAgo(t.created_at)}</span></div>
      <p className="mt-2 font-semibold leading-snug">{t.title_en}</p>
      <p className="mt-1 text-sm text-muted-foreground">{t.location_on_board}</p>
      <div className="mt-3 flex flex-wrap items-center gap-1.5 text-xs"><ShoreChip s={t.shore_status} /><span className="text-muted-foreground">{t.reporter_name ?? "Anonymous"}</span></div>
    </button>
  );
}

function Board() {
  const { t: openId } = Route.useSearch();
  const nav = useNavigate({ from: Route.fullPath });
  const q = useMasterTickets();
  const [seg, setSeg] = useState<ColumnDef["id"]>("NEW");
  const open = q.data?.find((x) => x.id === openId);
  const setOpen = (id?: string) => nav({ search: { t: id }, replace: true });
  const getColTickets = (colId: ColumnDef["id"]) => {
    const colDef = COLS.find((c) => c.id === colId);
    return q.data?.filter((t) => (colDef ? colDef.match(t) : false)) ?? [];
  };

  return (
    <div className="lg:max-w-none">
      <PageHeader title="Near-misses" subtitle={`${q.data?.filter((t) => !isResolvedByShore(t)).length ?? "–"} open on board`} />
      {q.isLoading ? <ListSkeleton /> : (
        <>
          <div className="mb-4 flex gap-1 overflow-x-auto rounded-2xl bg-muted p-1 md:hidden">
            {COLS.map((col) => (
              <button
                key={col.id}
                onClick={() => setSeg(col.id)}
                className={cn(
                  "tap shrink-0 rounded-xl px-3 text-xs font-medium",
                  seg === col.id ? "bg-card shadow-soft" : "text-muted-foreground"
                )}
              >
                {col.label} · {getColTickets(col.id).length}
              </button>
            ))}
          </div>
          <div className="space-y-3 md:hidden">
            {getColTickets(seg).map((t) => (
              <Card key={t.id} t={t} onOpen={() => setOpen(t.id)} />
            ))}
          </div>
          <div className="hidden gap-4 md:grid md:grid-cols-3">
            {COLS.map((col) => (
              <div key={col.id} className="space-y-3">
                <p className="flex items-center justify-between px-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  {col.label}
                  <span className="rounded-full bg-muted px-2 py-0.5">{getColTickets(col.id).length}</span>
                </p>
                {getColTickets(col.id).map((t) => (
                  <Card key={t.id} t={t} onOpen={() => setOpen(t.id)} />
                ))}
              </div>
            ))}
          </div>
        </>
      )}
      <Sheet open={!!open} onOpenChange={(o) => !o && setOpen(undefined)}>
        <SheetContent className="w-full overflow-y-auto sm:max-w-lg">
          {open && <Drawer t={open} />}
        </SheetContent>
      </Sheet>
    </div>
  );
}

function Drawer({ t }: { t: Ticket }) {
  const ack = useAckTicket();
  const add = useAddAction();
  const [text, setText] = useState("");
  const [rank, setRank] = useState("Bosun");
  const [due, setDue] = useState(() => new Date(Date.now() + 86_400_000).toISOString().slice(0, 16));
  const [photo, setPhoto] = useState<Blob | null>(null);
  const [cam, setCam] = useState(false);
  const save = async () => {
    await add.mutateAsync({ id: t.id, text, responsible_rank: rank, due_at: new Date(due).toISOString(), resolve: false, photo: photo ?? undefined });
    setText(""); setPhoto(null);
    toast.success("Action added.");
  };
  return (
    <div className="space-y-6 pb-8">
      <SheetHeader className="text-left">
        <div className="flex items-center gap-2 text-xs text-muted-foreground"><span className="font-mono">{t.ticket_no}</span><SeverityPill s={t.severity} /></div>
        <SheetTitle className="text-xl">{t.title_en}</SheetTitle>
        <p className="text-sm text-muted-foreground">{t.reporter_name ?? "Anonymous"} · {timeAgo(t.created_at)}</p>
      </SheetHeader>
      {t.onboard_status === "SUBMITTED" && (
        <Button className="h-12 w-full rounded-xl" onClick={() => ack.mutate(t.id)} disabled={ack.isPending}>{ack.isPending ? <Loader2 className="size-4 animate-spin" /> : <><Check className="size-4" />Acknowledge</>}</Button>
      )}
      <TicketBody t={t} />
      <div className="flex items-center gap-2 rounded-xl bg-muted/60 p-3 text-sm">Shore status (read-only): <ShoreChip s={t.shore_status} /></div>
      {!isResolvedByShore(t) && (
        <Section title="Add action">
          <div className="space-y-3 rounded-2xl border p-4">
            <Input value={text} onChange={(e) => setText(e.target.value)} placeholder="What will be done?" className="h-11 rounded-xl" aria-label="Action" />
            <div className="grid grid-cols-2 gap-2">
              <Select value={rank} onValueChange={setRank}><SelectTrigger className="h-11 rounded-xl" aria-label="Responsible rank"><SelectValue /></SelectTrigger><SelectContent>{RANKS.map((r) => <SelectItem key={r} value={r}>{r}</SelectItem>)}</SelectContent></Select>
              <Input type="datetime-local" value={due} onChange={(e) => setDue(e.target.value)} className="h-11 rounded-xl" aria-label="Due" />
            </div>
            <div className="flex items-center gap-3">
              <Button type="button" variant="secondary" className="h-11 rounded-xl" onClick={() => setCam(true)}><Camera className="size-4" />{photo ? "Retake photo" : "Photo of the fix"}</Button>
              {photo && <img src={URL.createObjectURL(photo)} alt="Fix" className="size-11 rounded-lg object-cover" />}
            </div>
            <Button className="h-11 w-full rounded-xl" disabled={!text || add.isPending} onClick={save}>Save action</Button>
          </div>
          <CameraSheet open={cam} onOpenChange={setCam} remaining={1} onCapture={setPhoto} />
        </Section>
      )}
      <Section title="Reply to reporter"><Thread ticketId={t.id} me="master" /></Section>
    </div>
  );
}
