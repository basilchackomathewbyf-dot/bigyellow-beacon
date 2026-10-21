import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useMutation } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Anchor, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { login } from "@/api/endpoints/auth";
import { authStore } from "@/lib/auth-store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import sea from "@/assets/login-sea.jpg";
import { track } from "@/lib/analytics";

export const Route = createFileRoute("/login")({
  head: () => ({
    meta: [
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
      { title: "Sign in — Beacon Dashboard" },
      { name: "description", content: "Sign in to the Beacon shore safety dashboard." },
      { property: "og:title", content: "Sign in — Beacon Dashboard" },
      { property: "og:description", content: "Sign in to the Beacon shore safety dashboard." },
    ],
  }),
  component: LoginPage,
});

function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const m = useMutation({
    mutationFn: (v: { email: string; password: string }) => login(v.email, v.password),
    onSuccess: (res) => {
      track("login_ok", { role: res.user.role ?? "unknown" });
      authStore.set(res.token, res.user);
      navigate({ to: "/tickets" });
    },
    onError: (e: Error) => {
      track("login_fail", { error_class: /401|password|email|invalid|match/i.test(e.message) ? "auth" : "other" });
      toast.error(e.message);
    },
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    m.mutate({ email, password });
  };

  return (
    <div className="grid min-h-screen lg:grid-cols-[1.1fr_1fr]">
      <div className="relative hidden overflow-hidden lg:block">
        <img src={sea} alt="" width={1024} height={1280} className="absolute inset-0 size-full object-cover" />
        <div className="absolute inset-0 bg-gradient-to-t from-foreground/70 via-foreground/10 to-transparent" />
        <div className="absolute bottom-0 p-12 text-primary-foreground">
          <p className="max-w-md text-3xl font-semibold leading-tight tracking-tight">{t("login.quote")}</p>
          <p className="mt-3 max-w-sm text-sm opacity-85">{t("login.quoteSub")}</p>
        </div>
      </div>
      <div className="flex items-center justify-center px-6 py-12">
        <form onSubmit={submit} className="w-full max-w-sm space-y-6 animate-fade-up">
          <div className="flex items-center gap-2.5">
            <span className="grid size-10 place-items-center rounded-xl sea-gradient text-primary-foreground shadow-[var(--shadow-soft)]">
              <Anchor className="size-5" aria-hidden />
            </span>
            <div>
              <div className="text-lg font-semibold tracking-tight">{t("app.name")}</div>
              <div className="text-xs text-muted-foreground">{t("app.tagline")}</div>
            </div>
          </div>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">{t("login.title")}</h1>
            <p className="mt-1 text-sm text-muted-foreground">{t("login.subtitle")}</p>
          </div>
          <div className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="email">{t("login.email")}</Label>
              <Input id="email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="password">{t("login.password")}</Label>
              <Input id="password" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
            </div>
          </div>
          <Button type="submit" className="w-full" disabled={m.isPending}>
            {m.isPending && <Loader2 className="animate-spin" />}
            {t("login.submit")}
          </Button>
          <div className="grid grid-cols-2 gap-2">
            <Button type="button" variant="outline" disabled={m.isPending} onClick={() => m.mutate({ email: "anita.rao@beacon-ship.com", password: "demo" })}>
              {t("login.demo")}
            </Button>
            <Button type="button" variant="outline" disabled={m.isPending} onClick={() => m.mutate({ email: "admin@beacon-ship.com", password: "demo" })}>
              {t("login.demoAdmin")}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
