import { createFileRoute, Outlet, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { useSession } from "@/lib/session";
import { AppShell } from "@/components/beacon/AppShell";
import { Logo } from "@/components/beacon/Logo";

export const Route = createFileRoute("/_app")({
  ssr: false,
  component: AppLayout,
});

function AppLayout() {
  const { user, ready } = useSession();
  const nav = useNavigate();
  useEffect(() => { if (ready && !user) nav({ to: "/login", replace: true }); }, [ready, user, nav]);
  if (!ready || !user) return <div className="grid min-h-dvh place-items-center"><Logo className="animate-pulse" /></div>;
  return <AppShell><Outlet /></AppShell>;
}
