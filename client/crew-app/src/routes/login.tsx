import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useRef, useState, useCallback } from "react";
import {
  Eye,
  EyeOff,
  Loader2,
  QrCode,
  Camera,
  CameraOff,
  CheckCircle2,
  Ship,
  KeyRound,
  UserCheck,
  RefreshCw,
  Sparkles,
  ShieldCheck,
  AlertCircle,
  Delete,
  Crown,
  Users,
  Clock,
} from "lucide-react";
import {
  login,
  pairDevice,
  loginWithDevice,
  getStoredDeviceToken,
  getStoredPairedInfo,
  getStoredLastCrew,
  setStoredLastCrew,
  setStoredDeviceToken,
  setStoredPairedInfo,
  DEMO_ACCOUNTS,
} from "@/api/endpoints/auth";
import { USE_MOCK } from "@/api/config";
import { useSession } from "@/lib/session";
import { Logo } from "@/components/beacon/Logo";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export const Route = createFileRoute("/login")({
  ssr: false,
  head: () => ({
    meta: [
      { title: "Sign in & Vessel Device Pairing — BigYellow Beacon" },
      { name: "description", content: "Pair shipboard crew device via bulkhead QR code or sign in with PIN pad." },
      { property: "og:title", content: "Sign in & Device Pairing — BigYellow Beacon" },
      { property: "og:description", content: "Pair shipboard crew device via bulkhead QR code or sign in with PIN pad." },
    ],
  }),
  component: Login,
});

const BULKHEAD_PRESETS = [
  { label: "Main Deck Bulkhead", code: "BEACON-QR-MV-PACIFIC-STAR" },
  { label: "Engine Control Room", code: "BEACON-QR-PACIFIC-STAR" },
  { label: "Gangway Watch Station", code: "DEMO-PAIR-123" },
];

export const CREW_ROSTER_PRESETS = [
  { id: "01a14acb-e04c-79f8-aa4e-0395dcf068d0", name: "Amarjeet", rank: "AB Seaman", dept: "Deck" },
  { id: "u-master", name: "Capt. Kundan", rank: "Master", dept: "Bridge" },
  { id: "u-3", name: "Jose Santos", rank: "Bosun", dept: "Deck" },
  { id: "u-4", name: "Olena Kovalenko", rank: "2nd Officer", dept: "Deck" },
  { id: "u-5", name: "Mark Dela Cruz", rank: "Oiler", dept: "Engine" },
  { id: "u-6", name: "Priya Sharma", rank: "3rd Engineer", dept: "Engine" },
  { id: "u-7", name: "Taras Melnyk", rank: "Chief Engineer", dept: "Engine" },
  { id: "u-8", name: "Ramon Bautista", rank: "Cook", dept: "Galley" },
];

const DEPARTMENTS = ["Deck", "Engine", "Galley", "Bridge", "Safety"];

function Login() {
  const nav = useNavigate();
  const { user, ready, signIn } = useSession();

  // Mode: "pair" (bulkhead QR onboarding), "pin" (PIN pad login for crew/master), "credentials" (officer login)
  const [mode, setMode] = useState<"pair" | "pin" | "credentials">("pair");

  // Pairing State
  const [pairingCode, setPairingCode] = useState("BEACON-QR-MV-PACIFIC-STAR");
  const [crewId, setCrewId] = useState("01a14acb-e04c-79f8-aa4e-0395dcf068d0");
  const [crewName, setCrewName] = useState("Amarjeet");
  const [department, setDepartment] = useState("Deck");
  const [pairPin, setPairPin] = useState("1234");

  // PIN Pad State: Crew (4-digit) vs Master (6-digit)
  const [pinRole, setPinRole] = useState<"crew" | "master">("crew");
  const [storedToken, setStoredToken] = useState<string | null>(null);
  const [pairedInfo, setPairedInfo] = useState<ReturnType<typeof getStoredPairedInfo>>(null);
  const [pinCode, setPinCode] = useState("");

  // Lockout State (15 min lockout after 5 failed attempts)
  const [lockoutSeconds, setLockoutSeconds] = useState<number>(0);
  const [remainingAttempts, setRemainingAttempts] = useState<number | null>(null);

  // Credentials State
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);

  // Common UI State
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  // Camera QR Scanner State
  const [scanning, setScanning] = useState(false);
  const [cameraError, setCameraError] = useState("");
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const scanIntervalRef = useRef<number | null>(null);

  const targetPinLength = pinRole === "master" ? 6 : 4;

  // Check existing session or paired device on mount
  useEffect(() => {
    if (ready && user) {
      nav({ to: user.role === "master" ? "/master/board" : "/home", replace: true });
      return;
    }

    const token = getStoredDeviceToken();
    const info = getStoredPairedInfo();
    if (token) {
      setStoredToken(token);
      setPairedInfo(info);
      if (info?.crew_id === "u-master" || info?.department === "Bridge") {
        setPinRole("master");
      }
      setMode("pin");
    }
  }, [ready, user, nav]);

  // Lockout countdown timer
  useEffect(() => {
    if (lockoutSeconds <= 0) return;
    const interval = setInterval(() => {
      setLockoutSeconds((s) => (s > 1 ? s - 1 : 0));
    }, 1000);
    return () => clearInterval(interval);
  }, [lockoutSeconds]);

  // Clean up camera stream
  const stopCamera = useCallback(() => {
    if (scanIntervalRef.current) {
      clearInterval(scanIntervalRef.current);
      scanIntervalRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setScanning(false);
  }, []);

  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, [stopCamera]);

  // Start Camera QR Scanning
  const startCamera = async () => {
    setCameraError("");
    setScanning(true);
    setErr("");

    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error("Camera API is not supported in this browser environment.");
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" }, width: { ideal: 640 }, height: { ideal: 480 } },
      });
      streamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play().catch(() => {});
      }

      // Continuous barcode detection if supported
      const hasBarcodeDetector = typeof window !== "undefined" && "BarcodeDetector" in window;
      if (hasBarcodeDetector) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const detector = new (window as any).BarcodeDetector({ formats: ["qr_code"] });
        scanIntervalRef.current = window.setInterval(async () => {
          if (!videoRef.current || videoRef.current.readyState < 2) return;
          try {
            const barcodes = await detector.detect(videoRef.current);
            if (barcodes && barcodes.length > 0) {
              const detected = barcodes[0].rawValue;
              if (detected) {
                setPairingCode(detected);
                setSuccessMsg(`QR Code Detected: ${detected}`);
                stopCamera();
              }
            }
          } catch {
            // Ignore frame decode errors
          }
        }, 400);
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Unable to access camera.";
      setCameraError(`${msg} Please enter code manually below.`);
      stopCamera();
    }
  };

  // Submit Bulkhead Device Pairing
  const handlePairSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pairingCode.trim()) {
      setErr("Please scan or enter a vessel bulkhead pairing code.");
      return;
    }

    setBusy(true);
    setErr("");
    setSuccessMsg("");

    try {
      // 1. POST /api/v1/auth/pair
      const pairRes = await pairDevice({
        pairing_code: pairingCode.trim(),
        crew_id: crewId.trim() || undefined,
        crew_name: crewName.trim() || undefined,
        department,
        pin: pairPin || "1234",
      });

      setSuccessMsg(`Vessel paired: ${pairRes.vessel_id}! Authenticating...`);

      // 2. Immediate device login using device_token + PIN
      const loginRes = await loginWithDevice(pairRes.device_token, pairPin || "1234");
      signIn(loginRes.user, loginRes.token);
      nav({ to: loginRes.user.role === "master" ? "/master/board" : "/home", replace: true });
    } catch (ex: unknown) {
      const msg = ex instanceof Error ? ex.message : "Failed to pair device to vessel bulkhead.";
      setErr(msg);
    } finally {
      setBusy(false);
    }
  };

  // Execute PIN Login
  const performPinLogin = useCallback(
    async (codeToSubmit: string) => {
      if (lockoutSeconds > 0) {
        setErr(`Device is temporarily locked. Please wait ${Math.ceil(lockoutSeconds / 60)} min.`);
        return;
      }

      setBusy(true);
      setErr("");

      try {
        let tokenToUse = storedToken;
        if (pinRole === "master") {
          tokenToUse = (pairedInfo?.department === "Bridge" || pairedInfo?.crew_id === "u-master") && storedToken
            ? storedToken
            : "master-console";
        } else {
          tokenToUse = storedToken || "crew-tablet";
        }

        const loginRes = await loginWithDevice(tokenToUse, codeToSubmit);
        setRemainingAttempts(null);
        signIn(loginRes.user, loginRes.token);
        nav({ to: loginRes.user.role === "master" ? "/master/board" : "/home", replace: true });
      } catch (ex: unknown) {
        setPinCode("");
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const errObj = ex as any;
        const msg = ex instanceof Error ? ex.message : "PIN verification failed.";

        if (errObj?.status === 423 || msg.includes("locked")) {
          setLockoutSeconds(15 * 60);
          setErr("Device locked for 15 minutes after 5 failed login attempts.");
        } else if (msg.includes("Remaining attempts")) {
          const match = msg.match(/Remaining attempts:\s*(\d+)/);
          if (match) setRemainingAttempts(parseInt(match[1], 10));
          setErr(msg);
        } else {
          setErr(msg);
        }
      } finally {
        setBusy(false);
      }
    },
    [lockoutSeconds, storedToken, pinRole, signIn, nav]
  );

  // Keypad Handlers
  const handleKeypadPress = (digit: string) => {
    if (lockoutSeconds > 0 || busy) return;
    if (pinCode.length < targetPinLength) {
      const next = pinCode + digit;
      setPinCode(next);
      if (next.length === targetPinLength) {
        void performPinLogin(next);
      }
    }
  };

  const handleKeypadBackspace = () => {
    if (lockoutSeconds > 0 || busy) return;
    setPinCode((prev) => prev.slice(0, -1));
  };

  const handleKeypadClear = () => {
    if (lockoutSeconds > 0 || busy) return;
    setPinCode("");
  };

  // Keyboard navigation for PIN Pad
  useEffect(() => {
    if (mode !== "pin") return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key >= "0" && e.key <= "9") {
        handleKeypadPress(e.key);
      } else if (e.key === "Backspace") {
        handleKeypadBackspace();
      } else if (e.key === "Escape") {
        handleKeypadClear();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [mode, pinCode, targetPinLength, lockoutSeconds, busy]);

  // Submit Officer / Web Credentials
  const handleCredentialsSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setErr("");
    try {
      const r = await login(username, password);
      signIn(r.user, r.token);
      nav({ to: r.user.role === "master" ? "/master/board" : "/home", replace: true });
    } catch {
      setErr("That username or password doesn't match. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  // Reset pairing to pair another crew member or scan different bulkhead
  const handleRePair = () => {
    setStoredDeviceToken(null);
    setStoredPairedInfo(null);
    setStoredToken(null);
    setPairedInfo(null);
    setPinCode("");
    setLockoutSeconds(0);
    setMode("pair");
    setErr("");
    setSuccessMsg("");
  };

  return (
    <div className="grid min-h-dvh lg:grid-cols-2">
      {/* Maritime Brand Column */}
      <div className="relative hidden overflow-hidden bg-ocean lg:block">
        <div className="absolute -left-20 -top-20 size-96 rounded-full bg-sun/40 blur-3xl" />
        <div className="absolute bottom-0 right-0 size-[28rem] rounded-full bg-coral/30 blur-3xl" />
        <div className="relative flex h-full flex-col justify-between p-14 text-primary-foreground">
          <div className="flex items-center gap-3">
            <div className="grid size-10 place-items-center rounded-2xl bg-card/20 backdrop-blur-md">
              <Ship className="size-6 text-sun" />
            </div>
            <div>
              <p className="font-semibold tracking-wider uppercase text-xs text-sun">Shipboard Edge Intelligence</p>
              <p className="text-sm font-medium opacity-90">MV Pacific Star • IMO 9412345</p>
            </div>
          </div>

          <div>
            <p className="font-display text-5xl font-extrabold leading-tight tracking-tight">
              Every report
              <br />
              brings a shipmate
              <br />
              <span className="text-sun">home safe.</span>
            </p>
            <p className="mt-4 max-w-sm text-primary-foreground/80">
              Near-misses, wellbeing and learning — paired directly from ship bulkheads with zero internet dependency.
            </p>
          </div>

          <div className="flex items-center gap-2 text-xs opacity-75">
            <ShieldCheck className="size-4 text-emerald-400" />
            <span>Encrypted local mesh • Argon2 protected device tokens</span>
          </div>
        </div>
      </div>

      {/* Interactive Authentication & Pairing Column */}
      <div className="flex items-center justify-center px-4 py-8 sm:px-8">
        <div className="w-full max-w-md space-y-6">
          <div className="flex items-center justify-between">
            <Logo size={42} />
            <div className="flex items-center gap-1.5 rounded-full border border-border bg-card/80 px-3 py-1 text-xs font-semibold text-muted-foreground shadow-xs">
              <span className="size-2 rounded-full bg-emerald-500 animate-pulse" />
              Edge Online
            </div>
          </div>

          {/* Userflow Mode Tabs */}
          <div className="grid grid-cols-3 gap-1 rounded-2xl bg-muted/60 p-1.5 text-xs font-semibold">
            <button
              type="button"
              onClick={() => {
                setMode("pair");
                setErr("");
              }}
              className={`flex items-center justify-center gap-1.5 rounded-xl py-2 transition-all ${
                mode === "pair" ? "bg-card text-foreground shadow-xs font-bold" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <QrCode className="size-3.5" />
              <span>Bulkhead QR</span>
            </button>
            <button
              type="button"
              onClick={() => {
                setMode("pin");
                setErr("");
              }}
              className={`flex items-center justify-center gap-1.5 rounded-xl py-2 transition-all ${
                mode === "pin" ? "bg-card text-foreground shadow-xs font-bold" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <KeyRound className="size-3.5" />
              <span>PIN Pad</span>
            </button>
            <button
              type="button"
              onClick={() => {
                setMode("credentials");
                setErr("");
              }}
              className={`flex items-center justify-center gap-1.5 rounded-xl py-2 transition-all ${
                mode === "credentials" ? "bg-card text-foreground shadow-xs font-bold" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <UserCheck className="size-3.5" />
              <span>Officer</span>
            </button>
          </div>

          {/* ============================================================ */}
          {/* TAB 1: BULKHEAD QR PAIRING (Main Userflow)                   */}
          {/* ============================================================ */}
          {mode === "pair" && (
            <form onSubmit={handlePairSubmit} className="space-y-5 rise">
              <div>
                <h1 className="text-2xl font-extrabold tracking-tight">Bulkhead Device Pairing</h1>
                <p className="mt-1 text-xs text-muted-foreground">
                  Scan the physical QR plate mounted on your watchstation bulkhead to authenticate your device.
                </p>
              </div>

              {/* QR Scanner Viewfinder or Trigger */}
              <div className="rounded-2xl border border-border bg-card p-3 shadow-xs space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="grid size-7 place-items-center rounded-lg bg-sun-soft text-foreground">
                      <QrCode className="size-4" />
                    </div>
                    <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Vessel Bulkhead Scanner</span>
                  </div>
                  {scanning ? (
                    <button
                      type="button"
                      onClick={stopCamera}
                      className="inline-flex items-center gap-1 rounded-lg bg-muted px-2 py-1 text-xs font-semibold text-foreground hover:bg-muted/80"
                    >
                      <CameraOff className="size-3.5" />
                      Close Lens
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={startCamera}
                      className="inline-flex items-center gap-1 rounded-lg bg-ocean/10 px-2.5 py-1 text-xs font-semibold text-ocean hover:bg-ocean/20 transition-colors"
                    >
                      <Camera className="size-3.5" />
                      Open Scanner
                    </button>
                  )}
                </div>

                {/* Live Video Viewfinder */}
                {scanning && (
                  <div className="relative aspect-video w-full overflow-hidden rounded-xl bg-black flex items-center justify-center">
                    <video ref={videoRef} autoPlay playsInline muted className="size-full object-cover" />
                    {/* Industrial Scanning Reticle */}
                    <div className="pointer-events-none absolute inset-0 grid place-items-center">
                      <div className="relative size-36 border-2 border-dashed border-sun/80 rounded-xl">
                        <div className="absolute -top-1 -left-1 size-4 border-t-2 border-l-2 border-sun" />
                        <div className="absolute -top-1 -right-1 size-4 border-t-2 border-r-2 border-sun" />
                        <div className="absolute -bottom-1 -left-1 size-4 border-b-2 border-l-2 border-sun" />
                        <div className="absolute -bottom-1 -right-1 size-4 border-b-2 border-r-2 border-sun" />
                        <div className="absolute inset-x-0 top-1/2 h-0.5 bg-sun shadow-glow animate-pulse" />
                      </div>
                    </div>
                    <div className="absolute bottom-2 inset-x-0 text-center">
                      <span className="rounded-full bg-black/60 px-3 py-1 text-[11px] font-medium text-white backdrop-blur-xs">
                        Align bulkhead QR inside reticle
                      </span>
                    </div>
                  </div>
                )}

                {cameraError && (
                  <div className="flex items-center gap-2 rounded-xl bg-amber-500/10 p-2 text-xs text-amber-700 dark:text-amber-300">
                    <AlertCircle className="size-4 shrink-0" />
                    <span>{cameraError}</span>
                  </div>
                )}

                {/* Bulkhead Code Input */}
                <div className="space-y-1">
                  <Label htmlFor="pairing_code" className="text-xs font-semibold">Bulkhead Pairing Code / QR Value</Label>
                  <div className="relative">
                    <Input
                      id="pairing_code"
                      value={pairingCode}
                      onChange={(e) => setPairingCode(e.target.value)}
                      placeholder="e.g. BEACON-QR-MV-PACIFIC-STAR"
                      className="h-11 rounded-xl bg-muted/40 font-mono text-xs pr-8"
                      required
                    />
                    {pairingCode && (
                      <CheckCircle2 className="size-4 text-emerald-500 absolute right-3 top-1/2 -translate-y-1/2" />
                    )}
                  </div>
                </div>

                {/* Bulkhead Plate Presets */}
                <div className="space-y-1">
                  <span className="text-[11px] font-medium text-muted-foreground">Bulkhead Stations on Board:</span>
                  <div className="flex flex-wrap gap-1.5">
                    {BULKHEAD_PRESETS.map((p) => (
                      <button
                        key={p.code}
                        type="button"
                        onClick={() => setPairingCode(p.code)}
                        className={`rounded-lg border px-2 py-1 text-[11px] font-medium transition-colors ${
                          pairingCode === p.code
                            ? "border-ocean bg-ocean/10 text-ocean font-bold"
                            : "border-border bg-card text-muted-foreground hover:bg-muted"
                        }`}
                      >
                        {p.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>



              {/* Status & Error Alerts */}
              {err && <p role="alert" className="rounded-xl bg-coral-soft px-3 py-2 text-xs text-foreground font-medium">{err}</p>}
              {successMsg && (
                <p className="rounded-xl bg-emerald-500/10 px-3 py-2 text-xs text-emerald-800 dark:text-emerald-200 font-medium flex items-center gap-1.5">
                  <CheckCircle2 className="size-4 shrink-0 text-emerald-600" />
                  <span>{successMsg}</span>
                </p>
              )}

              {/* Action Button */}
              <Button
                type="submit"
                disabled={busy || !pairingCode.trim()}
                className="h-12 w-full rounded-2xl bg-ocean py-3 text-sm font-semibold shadow-lift text-white hover:bg-ocean/90 cursor-pointer"
              >
                {busy ? (
                  <span className="flex items-center gap-2">
                    <Loader2 className="size-4 animate-spin" />
                    Pairing Device to Vessel...
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    <Sparkles className="size-4 text-sun" />
                    Pair Device & Enter Watch
                  </span>
                )}
              </Button>
            </form>
          )}

          {/* ============================================================ */}
          {/* TAB 2: PIN PAD LOGIN (Crew: 4 digits, Master: 6 digits)      */}
          {/* ============================================================ */}
          {mode === "pin" && (
            <div className="space-y-5 rise">
              <div>
                <h1 className="text-2xl font-extrabold tracking-tight">PIN Pad Terminal</h1>
              </div>

              {/* Role Toggle: Crew (4 digits) vs Master (6 digits) */}
              <div className="grid grid-cols-2 gap-2 rounded-2xl border border-border bg-card p-1.5 shadow-xs">
                <button
                  type="button"
                  onClick={() => {
                    setPinRole("crew");
                    setPinCode("");
                    setErr("");
                  }}
                  className={`flex items-center justify-center gap-2 rounded-xl py-2 text-xs font-semibold transition-all ${
                    pinRole === "crew"
                      ? "bg-ocean text-white font-bold shadow-xs"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <Users className="size-3.5" />
                  <span>Crew Watch (4-Digit)</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setPinRole("master");
                    setPinCode("");
                    setErr("");
                  }}
                  className={`flex items-center justify-center gap-2 rounded-xl py-2 text-xs font-semibold transition-all ${
                    pinRole === "master"
                      ? "bg-amber-600 text-white font-bold shadow-xs"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <Crown className="size-3.5" />
                  <span>Master Command (6-Digit)</span>
                </button>
              </div>

              {/* Device / Station Badge */}
              {(() => {
                const lastCrew = getStoredLastCrew();
                const cleanPairedName =
                  pairedInfo?.crew_name && pairedInfo.crew_name !== "Arjun Nair" && !/^[0-9a-f]{8}-[0-9a-f]{4}/i.test(pairedInfo.crew_name)
                    ? pairedInfo.crew_name
                    : null;
                const activeName =
                  pinRole === "master"
                    ? "Capt. Kundan"
                    : (lastCrew?.name && lastCrew.name !== "Arjun Nair"
                        ? lastCrew.name
                        : cleanPairedName || "Amarjeet");
                const activeDept =
                  pinRole === "master"
                    ? "Bridge Command"
                    : (lastCrew?.department || pairedInfo?.department || "Deck Watch");
                const activeVessel = lastCrew?.vessel || pairedInfo?.vessel_id || "MV Pacific Star";
                const initials = pinRole === "master" ? "MST" : activeName.slice(0, 2).toUpperCase();

                return (
                  <div className="rounded-2xl border border-border bg-card p-3 shadow-xs flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <div
                        className={`grid size-9 place-items-center rounded-xl font-bold text-xs ${
                          pinRole === "master" ? "bg-amber-500/10 text-amber-700" : "bg-ocean/10 text-ocean"
                        }`}
                      >
                        {initials}
                      </div>
                      <div>
                        <p className="text-xs font-bold text-foreground">
                          {pinRole === "master" ? "Capt. Kundan (Master Command)" : activeName}
                        </p>
                        <p className="text-[11px] text-muted-foreground flex items-center gap-1">
                          <span>{activeDept}</span>
                          <span>•</span>
                          <span>{activeVessel}</span>
                        </p>
                      </div>
                    </div>
                    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-bold text-emerald-700">
                      <ShieldCheck className="size-3" /> Secure PIN
                    </span>
                  </div>
                );
              })()}

              {/* Lockout Warning Banner */}
              {lockoutSeconds > 0 && (
                <div className="rounded-2xl bg-coral-soft p-3.5 text-xs text-foreground font-medium space-y-1 border border-destructive/20 animate-pulse">
                  <div className="flex items-center gap-2 font-bold text-destructive">
                    <Clock className="size-4 shrink-0" />
                    <span>Terminal Locked for Security</span>
                  </div>
                  <p className="text-[11px] text-muted-foreground">
                    Too many incorrect attempts. Unlocks in:{" "}
                    <span className="font-mono font-bold text-foreground">
                      {Math.floor(lockoutSeconds / 60)}:{(lockoutSeconds % 60).toString().padStart(2, "0")}
                    </span>
                  </p>
                </div>
              )}

              {/* Error & Remaining Attempts Alert */}
              {err && lockoutSeconds <= 0 && (
                <p role="alert" className="rounded-xl bg-coral-soft px-3 py-2 text-xs text-foreground font-medium">
                  {err}
                </p>
              )}

              {remainingAttempts !== null && remainingAttempts > 0 && lockoutSeconds <= 0 && (
                <p className="text-center text-[11px] font-semibold text-amber-600 dark:text-amber-400">
                  ⚠️ {remainingAttempts} attempts remaining before 15-minute lock
                </p>
              )}

              {/* PIN Slot Indicators */}
              <div className="flex justify-center items-center gap-3 py-2">
                {Array.from({ length: targetPinLength }).map((_, idx) => {
                  const isFilled = idx < pinCode.length;
                  const isCurrent = idx === pinCode.length && lockoutSeconds <= 0;
                  return (
                    <div
                      key={idx}
                      className={`grid size-12 place-items-center rounded-2xl border transition-all text-xl font-bold font-mono ${
                        isFilled
                          ? "border-ocean bg-ocean text-white shadow-xs"
                          : isCurrent
                          ? "border-ocean/70 bg-card ring-2 ring-ocean/30 ring-offset-2"
                          : "border-border bg-card/60 text-muted-foreground"
                      }`}
                    >
                      {isFilled ? "●" : ""}
                    </div>
                  );
                })}
              </div>

              {/* Tactile On-Screen Numeric Keypad */}
              <div className="grid grid-cols-3 gap-2.5 max-w-xs mx-auto">
                {["1", "2", "3", "4", "5", "6", "7", "8", "9"].map((digit) => (
                  <button
                    key={digit}
                    type="button"
                    disabled={lockoutSeconds > 0 || busy || pinCode.length >= targetPinLength}
                    onClick={() => handleKeypadPress(digit)}
                    className="grid h-13 place-items-center rounded-2xl border border-border bg-card text-xl font-bold text-foreground shadow-xs hover:bg-muted active:scale-95 disabled:opacity-40 transition-all cursor-pointer"
                  >
                    {digit}
                  </button>
                ))}

                <button
                  type="button"
                  disabled={lockoutSeconds > 0 || busy || pinCode.length === 0}
                  onClick={handleKeypadClear}
                  className="grid h-13 place-items-center rounded-2xl border border-border bg-card/50 text-xs font-bold text-muted-foreground hover:bg-muted active:scale-95 disabled:opacity-40 transition-all cursor-pointer"
                >
                  CLR
                </button>

                <button
                  type="button"
                  disabled={lockoutSeconds > 0 || busy || pinCode.length >= targetPinLength}
                  onClick={() => handleKeypadPress("0")}
                  className="grid h-13 place-items-center rounded-2xl border border-border bg-card text-xl font-bold text-foreground shadow-xs hover:bg-muted active:scale-95 disabled:opacity-40 transition-all cursor-pointer"
                >
                  0
                </button>

                <button
                  type="button"
                  disabled={lockoutSeconds > 0 || busy || pinCode.length === 0}
                  onClick={handleKeypadBackspace}
                  className="grid h-13 place-items-center rounded-2xl border border-border bg-card/50 text-foreground hover:bg-muted active:scale-95 disabled:opacity-40 transition-all cursor-pointer"
                >
                  <Delete className="size-5 text-muted-foreground" />
                </button>
              </div>

              {/* Submit Button */}
              <Button
                type="button"
                onClick={() => performPinLogin(pinCode)}
                disabled={busy || lockoutSeconds > 0 || pinCode.length !== targetPinLength}
                className="h-12 w-full rounded-2xl bg-ocean py-3 text-sm font-semibold shadow-lift text-white hover:bg-ocean/90 cursor-pointer"
              >
                {busy ? (
                  <span className="flex items-center gap-2">
                    <Loader2 className="size-4 animate-spin" /> Verifying Argon2 Hash...
                  </span>
                ) : (
                  <span>Unlock & Enter Watch ({targetPinLength} digits)</span>
                )}
              </Button>

              <div className="text-center">
                <button
                  type="button"
                  onClick={handleRePair}
                  className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground font-medium transition-colors cursor-pointer"
                >
                  <RefreshCw className="size-3" />
                  Pair a different crew member or scan new bulkhead QR
                </button>
              </div>
            </div>
          )}

          {/* ============================================================ */}
          {/* TAB 3: CREDENTIALS LOGIN (Master / Officer / Shore)          */}
          {/* ============================================================ */}
          {mode === "credentials" && (
            <form onSubmit={handleCredentialsSubmit} className="space-y-5 rise">
              <div>
                <h1 className="text-2xl font-extrabold tracking-tight">Master & Officer Sign In</h1>
                <p className="mt-1 text-xs text-muted-foreground">Sign in with officer username and security credentials.</p>
              </div>

              <div className="space-y-3">
                <div className="space-y-1">
                  <Label htmlFor="u" className="text-xs font-semibold">Username</Label>
                  <Input
                    id="u"
                    autoComplete="username"
                    autoCapitalize="none"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="e.g. master or crew"
                    className="h-11 rounded-xl bg-card text-xs"
                    required
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="p" className="text-xs font-semibold">Password</Label>
                  <div className="relative">
                    <Input
                      id="p"
                      type={show ? "text" : "password"}
                      autoComplete="current-password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      className="h-11 rounded-xl bg-card pr-10 text-xs"
                      required
                    />
                    <button
                      type="button"
                      aria-label={show ? "Hide password" : "Show password"}
                      onClick={() => setShow((s) => !s)}
                      className="tap absolute right-2 top-1/2 grid -translate-y-1/2 place-items-center text-muted-foreground hover:text-foreground"
                    >
                      {show ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                    </button>
                  </div>
                </div>
                {err && <p role="alert" className="rounded-xl bg-coral-soft px-3 py-2 text-xs text-foreground font-medium">{err}</p>}
              </div>

              <Button
                type="submit"
                disabled={busy || !username || !password}
                className="h-12 w-full rounded-2xl bg-ocean py-3 text-sm font-semibold shadow-lift text-white hover:bg-ocean/90 cursor-pointer"
              >
                {busy ? <Loader2 className="size-4 animate-spin" /> : "Sign in"}
              </Button>

              {USE_MOCK && (
                <div className="rounded-2xl bg-sun-soft p-3 text-xs">
                  <p className="font-semibold text-foreground">Demo officer credentials</p>
                  <div className="mt-2 grid grid-cols-1 gap-1">
                    {DEMO_ACCOUNTS.map((a) => (
                      <button
                        key={a.username}
                        type="button"
                        onClick={() => {
                          setUsername(a.username);
                          setPassword(a.password);
                        }}
                        className="flex justify-between rounded-lg px-2 py-1 text-left hover:bg-card/70 text-xs"
                      >
                        <span className="text-muted-foreground">{a.label}</span>
                        <span className="font-mono text-foreground font-semibold">{a.username} / {a.password}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
