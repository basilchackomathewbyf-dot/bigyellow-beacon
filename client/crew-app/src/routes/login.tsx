import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Eye, EyeOff, Loader2 } from "lucide-react";
import logo from "@/assets/logo.png";
import { login } from "@/api/endpoints/auth";
import { useSession } from "@/lib/session";
import { Label } from "@/components/ui/label";

export const Route = createFileRoute("/login")({
  ssr: false,
  head: () => ({
    meta: [
      { title: "Sign in — BigYellow Beacon" },
      { name: "description", content: "Sign in to Beacon using your username and password." },
      { property: "og:title", content: "Sign in — BigYellow Beacon" },
      { property: "og:description", content: "Sign in to Beacon using your username and password." },
    ],
  }),
  component: Login,
});

export const CREW_ROSTER_PRESETS = [
  { id: "01a14acb-e04c-79f8-aa4e-0395dcf068d0", name: "Amarjeet", rank: "AB Seaman", dept: "Deck" },
  { id: "u-master", name: "Capt. Kundan", rank: "Master", dept: "Bridge" },
];

function Login() {
  const nav = useNavigate();
  const { user, ready, signIn } = useSession();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  // Redirect if already logged in
  useEffect(() => {
    if (ready && user) {
      nav({ to: user.role === "master" ? "/master/board" : "/home", replace: true });
    }
  }, [ready, user, nav]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim()) {
      setErr("Please enter your username.");
      return;
    }
    if (!password) {
      setErr("Please enter your password.");
      return;
    }

    setBusy(true);
    setErr("");

    try {
      const r = await login(username.trim(), password);
      signIn(r.user, r.token);
      nav({ to: r.user.role === "master" ? "/master/board" : "/home", replace: true });
    } catch (ex: unknown) {
      const msg = ex instanceof Error ? ex.message : "That username or password doesn't match.";
      setErr(msg);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen w-full bg-[#fbf7f1] dark:bg-background flex flex-col justify-center items-center px-6 py-12 transition-colors">
      <div className="w-full max-w-sm sm:max-w-md">
        {/* Brand Logo */}
        <div className="flex items-center gap-3">
          <img
            src={logo}
            alt="Beacon"
            width={44}
            height={44}
            className="size-11 drop-shadow-sm rounded-xl object-contain"
          />
          <span className="font-display text-2xl font-extrabold tracking-tight text-foreground">
            Beacon<span className="text-[#f59e0b]">.</span>
          </span>
        </div>

        {/* Header Heading */}
        <div className="mt-8 space-y-2">
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-slate-900 dark:text-foreground">
            Welcome aboard
          </h1>
          <p className="text-base sm:text-lg text-slate-500 dark:text-muted-foreground">
            Sign in to continue.
          </p>
        </div>

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="mt-8 space-y-6">
          <div className="space-y-2">
            <Label htmlFor="username" className="text-sm font-semibold text-slate-800 dark:text-foreground">
              Username
            </Label>
            <input
              id="username"
              type="text"
              autoComplete="username"
              autoCapitalize="none"
              placeholder=""
              value={username}
              onChange={(e) => {
                setUsername(e.target.value);
                if (err) setErr("");
              }}
              className="w-full h-14 rounded-full border border-[#d6dfeb] bg-white px-6 text-base text-slate-900 shadow-xs transition-all focus:outline-none focus:border-[#73b4aa] focus:ring-4 focus:ring-[#73b4aa]/15 dark:bg-card dark:border-border dark:text-foreground"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="password" className="text-sm font-semibold text-slate-800 dark:text-foreground">
              Password
            </Label>
            <div className="relative">
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                placeholder=""
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  if (err) setErr("");
                }}
                className="w-full h-14 rounded-full border border-[#d6dfeb] bg-white pl-6 pr-14 text-base text-slate-900 shadow-xs transition-all focus:outline-none focus:border-[#73b4aa] focus:ring-4 focus:ring-[#73b4aa]/15 dark:bg-card dark:border-border dark:text-foreground"
              />
              <button
                type="button"
                onClick={() => setShowPassword((prev) => !prev)}
                className="absolute right-4 top-1/2 -translate-y-1/2 p-2 text-slate-400 hover:text-slate-600 dark:hover:text-foreground transition-colors"
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <EyeOff className="size-5" /> : <Eye className="size-5" />}
              </button>
            </div>
          </div>

          {err && (
            <div className="rounded-2xl border border-destructive/20 bg-destructive/10 p-3.5 text-center text-sm font-medium text-destructive animate-in fade-in duration-200">
              {err}
            </div>
          )}

          <button
            type="submit"
            disabled={busy || !username.trim() || !password}
            className="w-full h-14 rounded-full bg-[#73b4aa] hover:bg-[#62a399] active:scale-[0.99] text-white text-base font-semibold shadow-sm transition-all flex items-center justify-center disabled:opacity-50 disabled:pointer-events-none"
          >
            {busy ? (
              <>
                <Loader2 className="mr-2 size-5 animate-spin" />
                Signing in...
              </>
            ) : (
              "Sign in"
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
