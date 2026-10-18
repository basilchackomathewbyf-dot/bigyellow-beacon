import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Check, Copy, KeyRound, Loader2, Plus, Smartphone, Trash2, UserPlus, Users } from "lucide-react";
import { toast } from "sonner";
import {
  useCrewList,
  useCreateCrew,
  useDeleteCrew,
  useDevices,
  useLearningStats,
  useRevokeDevice,
} from "@/hooks/queries";
import type { CrewMember } from "@/api/endpoints/master";
import { RANKS } from "@/lib/labels";
import { ListSkeleton, PageHeader, Section } from "@/components/beacon/bits";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export const Route = createFileRoute("/_app/master/crew")({
  head: () => ({
    meta: [
      { title: "Crew & Accounts — Beacon" },
      { name: "description", content: "Manage shipboard crew accounts, credentials, and devices." },
      { property: "og:title", content: "Crew & Accounts — Beacon" },
      { property: "og:description", content: "Manage shipboard crew accounts and credentials." },
    ],
  }),
  component: Crew,
});

function Crew() {
  const crewQuery = useCrewList();
  const createCrew = useCreateCrew();
  const deleteCrew = useDeleteCrew();
  const dev = useDevices();
  const revoke = useRevokeDevice();
  const stats = useLearningStats();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [name, setName] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("1234");
  const [rank, setRank] = useState("AB Seaman");
  const [recentHandoff, setRecentHandoff] = useState<{
    member: CrewMember;
    rawPassword: string;
  } | null>(null);

  const handleNameChange = (val: string) => {
    setName(val);
    if (!username || username === name.toLowerCase().replace(/[^a-z0-9]/g, "")) {
      setUsername(val.toLowerCase().replace(/[^a-z0-9]/g, "").slice(0, 16));
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !username.trim() || !password.trim()) {
      toast.error("Please fill in all fields");
      return;
    }

    try {
      const created = await createCrew.mutateAsync({
        name: name.trim(),
        username: username.trim().toLowerCase(),
        password: password.trim(),
        rank,
      });

      setRecentHandoff({ member: created, rawPassword: password.trim() });
      setDialogOpen(false);
      setName("");
      setUsername("");
      setPassword("1234");
      setRank("AB Seaman");
      toast.success(`Account created for ${created.name}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to create crew member";
      toast.error(msg);
    }
  };

  const copyCredentials = (u: string, p: string, crewName: string) => {
    const text = `Beacon Login Credentials for ${crewName}:\nUsername: ${u}\nPassword: ${p}\nURL: ${window.location.origin}/login`;
    navigator.clipboard.writeText(text);
    toast.success("Credentials copied to clipboard!");
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <PageHeader
          title="Crew Management"
          subtitle="Manage shipboard crew accounts, login credentials, and devices."
        />
        <Button
          onClick={() => setDialogOpen(true)}
          className="gap-2 rounded-2xl bg-ocean px-5 py-2.5 font-semibold text-white shadow-lift"
        >
          <UserPlus className="size-4" />
          Add Crew Member
        </Button>
      </div>

      {/* Hand-off Notice Card for Master */}
      {recentHandoff && (
        <div className="surface border-2 border-sun/60 bg-sun-soft/30 p-5 rounded-3xl rise">
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="flex size-7 items-center justify-center rounded-full bg-sun text-ocean font-bold text-xs">
                  <Check className="size-4" />
                </span>
                <h3 className="font-semibold text-base">Account Created Ready for Handover</h3>
              </div>
              <p className="text-sm text-muted-foreground">
                Provide these login credentials to <strong className="text-foreground">{recentHandoff.member.name}</strong> ({recentHandoff.member.rank}).
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                copyCredentials(
                  recentHandoff.member.username,
                  recentHandoff.rawPassword,
                  recentHandoff.member.name
                )
              }
              className="shrink-0 gap-1.5 rounded-xl border-ocean/20 text-ocean hover:bg-ocean/10"
            >
              <Copy className="size-3.5" />
              Copy Info
            </Button>
          </div>

          <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-3 rounded-2xl bg-card p-3.5 text-sm border">
            <div>
              <span className="text-xs text-muted-foreground block">Full Name</span>
              <span className="font-semibold">{recentHandoff.member.name}</span>
            </div>
            <div>
              <span className="text-xs text-muted-foreground block">Username</span>
              <code className="font-mono font-bold text-ocean">{recentHandoff.member.username}</code>
            </div>
            <div>
              <span className="text-xs text-muted-foreground block">Initial Password</span>
              <code className="font-mono font-bold text-coral">{recentHandoff.rawPassword}</code>
            </div>
          </div>
        </div>
      )}

      {/* Crew Accounts List */}
      <Section title="Shipboard Crew Accounts">
        {crewQuery.isLoading ? (
          <ListSkeleton n={3} />
        ) : (
          <div className="surface divide-y p-0 overflow-hidden rounded-3xl border shadow-soft">
            {crewQuery.data && crewQuery.data.length > 0 ? (
              crewQuery.data.map((c) => (
                <div key={c.id} className="flex items-center justify-between p-4 px-5 transition hover:bg-muted/30">
                  <div className="flex items-center gap-3.5 min-w-0">
                    <div className="flex size-10 shrink-0 items-center justify-center rounded-2xl bg-ocean-soft text-ocean font-bold text-sm">
                      {c.name.slice(0, 2).toUpperCase()}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <p className="truncate font-semibold text-sm">{c.name}</p>
                        <span className="rounded-full bg-muted px-2 py-0.5 text-[11px] font-medium text-muted-foreground uppercase tracking-wide">
                          {c.rank}
                        </span>
                      </div>
                      <div className="flex items-center gap-3 text-xs text-muted-foreground mt-0.5">
                        <span className="flex items-center gap-1 font-mono">
                          <KeyRound className="size-3 text-muted-foreground" />
                          user: <strong className="text-foreground">{c.username}</strong>
                        </span>
                        <span>•</span>
                        <span>role: {c.role}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => copyCredentials(c.username, "1234", c.name)}
                      className="text-xs text-muted-foreground hover:text-foreground"
                      title="Copy login instructions"
                    >
                      <Copy className="size-3.5" />
                    </Button>
                    {c.username !== "crew" && c.username !== "master" && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          if (confirm(`Remove account for ${c.name}?`)) {
                            deleteCrew.mutate(c.id);
                            toast.success(`Removed ${c.name}`);
                          }
                        }}
                        className="text-xs text-coral hover:bg-coral-soft/50 hover:text-coral"
                      >
                        <Trash2 className="size-3.5" />
                      </Button>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <div className="p-8 text-center text-muted-foreground">
                <Users className="mx-auto size-8 opacity-40 mb-2" />
                <p>No crew accounts added yet.</p>
              </div>
            )}
          </div>
        )}
      </Section>

      {/* Learning Progress */}
      <Section title="Learning acknowledgements">
        <div className="surface space-y-4 p-5 rounded-3xl border shadow-soft">
          {stats.data?.map((s) => (
            <div key={s.learning_id} className="space-y-1.5">
              <div className="flex justify-between text-sm">
                <span className="font-medium">{s.title}</span>
                <span className="tabular-nums text-muted-foreground">
                  {s.acked}/{s.total}
                </span>
              </div>
              <Progress value={(s.acked / s.total) * 100} className="h-2" />
            </div>
          )) ?? <ListSkeleton n={2} />}
        </div>
      </Section>

      {/* Paired Devices */}
      <Section title="Paired Ship Devices">
        {dev.isLoading ? (
          <ListSkeleton />
        ) : (
          <ul className="surface divide-y p-0 overflow-hidden rounded-3xl border shadow-soft">
            {dev.data && dev.data.length > 0 ? (
              dev.data.map((d) => (
                <li key={d.id} className="flex items-center gap-3 p-4 px-5">
                  <Smartphone className="size-5 text-muted-foreground" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium text-sm">{d.crew_name}</p>
                    <p className="text-xs text-muted-foreground">
                      {d.rank} · paired {new Date(d.paired_at).toLocaleDateString()}
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-muted-foreground hover:text-coral"
                    onClick={() => revoke.mutate(d.id)}
                  >
                    Revoke
                  </Button>
                </li>
              ))
            ) : (
              <li className="p-6 text-center text-sm text-muted-foreground">
                No paired hardware devices currently active.
              </li>
            )}
          </ul>
        )}
      </Section>

      {/* Create Crew Account Modal Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md rounded-3xl">
          <form onSubmit={handleCreate}>
            <DialogHeader>
              <DialogTitle className="text-xl font-bold flex items-center gap-2">
                <UserPlus className="size-5 text-ocean" />
                Add Shipboard Crew Member
              </DialogTitle>
              <DialogDescription className="text-sm">
                Create a login account for a crew member. You can hand them their username and password so they can sign in from their phone or terminal.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <div className="space-y-1.5">
                <Label htmlFor="crew-name">Full Name</Label>
                <Input
                  id="crew-name"
                  placeholder="e.g. Vikram Patel"
                  value={name}
                  onChange={(e) => handleNameChange(e.target.value)}
                  className="h-11 rounded-xl"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label htmlFor="crew-username">Username</Label>
                  <Input
                    id="crew-username"
                    placeholder="e.g. vikram"
                    value={username}
                    onChange={(e) => setUsername(e.target.value.toLowerCase().replace(/[^a-z0-9_.-]/g, ""))}
                    className="h-11 rounded-xl font-mono text-sm"
                    required
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="crew-password">Initial Password / PIN</Label>
                  <Input
                    id="crew-password"
                    placeholder="e.g. 1234"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="h-11 rounded-xl font-mono text-sm"
                    required
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="crew-rank">Shipboard Rank / Role</Label>
                <Select value={rank} onValueChange={setRank}>
                  <SelectTrigger id="crew-rank" className="h-11 rounded-xl">
                    <SelectValue placeholder="Select rank" />
                  </SelectTrigger>
                  <SelectContent className="max-h-56">
                    {RANKS.map((r) => (
                      <SelectItem key={r} value={r}>
                        {r}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <DialogFooter className="gap-2 sm:gap-0">
              <Button
                type="button"
                variant="outline"
                onClick={() => setDialogOpen(false)}
                className="rounded-xl"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={createCrew.isPending || !name.trim() || !username.trim()}
                className="rounded-xl bg-ocean text-white font-semibold gap-1.5"
              >
                {createCrew.isPending && <Loader2 className="size-4 animate-spin" />}
                Create Account
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
