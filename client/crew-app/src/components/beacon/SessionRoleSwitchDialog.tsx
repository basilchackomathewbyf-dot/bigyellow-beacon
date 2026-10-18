import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { toast } from "sonner";
import {
  Crown,
  Users,
  ShieldCheck,
  KeyRound,
  Loader2,
  RefreshCw,
  Clock,
  ArrowLeftRight,
} from "lucide-react";
import { useSession } from "@/lib/session";
import { loginWithDevice, getStoredDeviceToken } from "@/api/endpoints/auth";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

interface SessionRoleSwitchDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function SessionRoleSwitchDialog({ open, onOpenChange }: SessionRoleSwitchDialogProps) {
  const { user, signIn } = useSession();
  const nav = useNavigate();

  const isCurrentMaster = user?.role === "master";
  const [targetRole, setTargetRole] = useState<"crew" | "master">(isCurrentMaster ? "crew" : "master");
  const [pinCode, setPinCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [lockoutSeconds, setLockoutSeconds] = useState(0);

  const targetPinLength = targetRole === "master" ? 6 : 4;

  const handleRoleSelect = (role: "crew" | "master") => {
    setTargetRole(role);
    setPinCode("");
    setErr("");
  };

  const handleKeypadPress = (digit: string) => {
    if (lockoutSeconds > 0 || busy) return;
    if (pinCode.length < targetPinLength) {
      const next = pinCode + digit;
      setPinCode(next);
      if (next.length === targetPinLength) {
        void executeSwitch(next);
      }
    }
  };

  const executeSwitch = async (code: string) => {
    setBusy(true);
    setErr("");

    try {
      let tokenToUse: string;
      if (targetRole === "master") {
        tokenToUse = "master-console";
      } else {
        tokenToUse = getStoredDeviceToken() || "crew-tablet";
      }

      const res = await loginWithDevice(tokenToUse, code);
      signIn(res.user, res.token);
      toast.success(`Switched session to ${res.user.name} (${res.user.role === "master" ? "Master" : "Crew"})`);
      onOpenChange(false);
      setPinCode("");

      nav({ to: res.user.role === "master" ? "/master/board" : "/home", replace: true });
    } catch (ex: unknown) {
      setPinCode("");
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const errObj = ex as any;
      const msg = ex instanceof Error ? ex.message : "Role switch failed.";
      if (errObj?.status === 423 || msg.includes("locked")) {
        setLockoutSeconds(15 * 60);
        setErr("Device locked for 15 minutes after 5 failed login attempts.");
      } else {
        setErr(msg);
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-sm rounded-3xl p-5 border border-border bg-card">
        <DialogHeader className="text-left space-y-1">
          <div className="flex items-center gap-2">
            <div className="grid size-8 place-items-center rounded-xl bg-ocean/10 text-ocean">
              <ArrowLeftRight className="size-4" />
            </div>
            <DialogTitle className="text-lg font-extrabold tracking-tight">
              Switch Watch Session
            </DialogTitle>
          </div>
          <DialogDescription className="text-xs text-muted-foreground">
            Current active watch: <span className="font-semibold text-foreground">{user?.name}</span> ({user?.role === "master" ? "Master Command" : "Crew Watch"}).
          </DialogDescription>
        </DialogHeader>

        {/* Target Role Selector */}
        <div className="grid grid-cols-2 gap-2 pt-1">
          <button
            type="button"
            onClick={() => handleRoleSelect("crew")}
            className={`flex flex-col items-center justify-center p-3 rounded-2xl border text-center transition-all cursor-pointer ${
              targetRole === "crew"
                ? "border-ocean bg-ocean/10 ring-2 ring-ocean/30 shadow-xs"
                : "border-border bg-card/60 hover:bg-muted opacity-70"
            }`}
          >
            <div className="grid size-8 place-items-center rounded-xl bg-ocean/10 text-ocean mb-1">
              <Users className="size-4" />
            </div>
            <span className="text-xs font-bold text-foreground">Crew Watch</span>
            <span className="text-[10px] text-muted-foreground">4-digit PIN</span>
          </button>

          <button
            type="button"
            onClick={() => handleRoleSelect("master")}
            className={`flex flex-col items-center justify-center p-3 rounded-2xl border text-center transition-all cursor-pointer ${
              targetRole === "master"
                ? "border-amber-600 bg-amber-500/10 ring-2 ring-amber-600/30 shadow-xs"
                : "border-border bg-card/60 hover:bg-muted opacity-70"
            }`}
          >
            <div className="grid size-8 place-items-center rounded-xl bg-amber-500/10 text-amber-700 mb-1">
              <Crown className="size-4" />
            </div>
            <span className="text-xs font-bold text-foreground">Master Bridge</span>
            <span className="text-[10px] text-muted-foreground">6-digit PIN</span>
          </button>
        </div>

        {/* Lockout Warning */}
        {lockoutSeconds > 0 && (
          <div className="rounded-xl bg-coral-soft p-3 text-xs text-foreground font-medium flex items-center gap-2">
            <Clock className="size-4 shrink-0 text-destructive" />
            <span>Terminal locked for 15 minutes due to failed attempts.</span>
          </div>
        )}

        {/* Error Alert */}
        {err && lockoutSeconds <= 0 && (
          <p className="rounded-xl bg-coral-soft px-3 py-2 text-xs text-foreground font-medium">
            {err}
          </p>
        )}

        {/* PIN Slot Indicators */}
        <div className="flex justify-center items-center gap-2.5 py-1">
          {Array.from({ length: targetPinLength }).map((_, idx) => {
            const isFilled = idx < pinCode.length;
            const isCurrent = idx === pinCode.length && lockoutSeconds <= 0;
            return (
              <div
                key={idx}
                className={`grid size-11 place-items-center rounded-xl border transition-all text-lg font-bold font-mono ${
                  isFilled
                    ? "border-ocean bg-ocean text-white shadow-xs"
                    : isCurrent
                    ? "border-ocean/70 bg-card ring-2 ring-ocean/30"
                    : "border-border bg-muted/40 text-muted-foreground"
                }`}
              >
                {isFilled ? "●" : ""}
              </div>
            );
          })}
        </div>

        {/* Tactile Keypad */}
        <div className="grid grid-cols-3 gap-2 max-w-[260px] mx-auto">
          {["1", "2", "3", "4", "5", "6", "7", "8", "9"].map((digit) => (
            <button
              key={digit}
              type="button"
              disabled={lockoutSeconds > 0 || busy || pinCode.length >= targetPinLength}
              onClick={() => handleKeypadPress(digit)}
              className="grid h-11 place-items-center rounded-xl border border-border bg-card text-lg font-bold text-foreground shadow-xs hover:bg-muted active:scale-95 disabled:opacity-40 transition-all cursor-pointer"
            >
              {digit}
            </button>
          ))}
          <button
            type="button"
            disabled={lockoutSeconds > 0 || busy || pinCode.length === 0}
            onClick={() => setPinCode("")}
            className="grid h-11 place-items-center rounded-xl border border-border bg-card/60 text-xs font-bold text-muted-foreground hover:bg-muted active:scale-95 disabled:opacity-40 cursor-pointer"
          >
            CLR
          </button>
          <button
            type="button"
            disabled={lockoutSeconds > 0 || busy || pinCode.length >= targetPinLength}
            onClick={() => handleKeypadPress("0")}
            className="grid h-11 place-items-center rounded-xl border border-border bg-card text-lg font-bold text-foreground shadow-xs hover:bg-muted active:scale-95 disabled:opacity-40 cursor-pointer"
          >
            0
          </button>
          <button
            type="button"
            disabled={lockoutSeconds > 0 || busy || pinCode.length === 0}
            onClick={() => setPinCode((prev) => prev.slice(0, -1))}
            className="grid h-11 place-items-center rounded-xl border border-border bg-card/60 text-xs font-bold text-foreground hover:bg-muted active:scale-95 disabled:opacity-40 cursor-pointer"
          >
            ⌫
          </button>
        </div>

        {/* Action Button */}
        <Button
          type="button"
          onClick={() => executeSwitch(pinCode)}
          disabled={busy || lockoutSeconds > 0 || pinCode.length !== targetPinLength}
          className="h-11 w-full rounded-xl bg-ocean py-2 text-sm font-semibold text-white hover:bg-ocean/90 cursor-pointer"
        >
          {busy ? (
            <span className="flex items-center gap-2">
              <Loader2 className="size-4 animate-spin" /> Verifying PIN...
            </span>
          ) : (
            <span>Switch to {targetRole === "master" ? "Master Command" : "Crew Watch"}</span>
          )}
        </Button>
      </DialogContent>
    </Dialog>
  );
}
