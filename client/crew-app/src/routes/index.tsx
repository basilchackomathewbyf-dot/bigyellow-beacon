import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { useSession } from "@/lib/session";
import { Logo } from "@/components/beacon/Logo";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "BigYellow Beacon — Safer, kinder watches" },
      { name: "description", content: "Report near-misses by voice or photo, check in on how you feel, and learn from the fleet." },
      { property: "og:title", content: "BigYellow Beacon" },
      { property: "og:description", content: "Near-miss reporting, wellbeing and learning for merchant ship crew." },
    ],
  }),
  component: Index,
});

function Index() {
  const { user, ready } = useSession();
  const nav = useNavigate();
  useEffect(() => {
    if (!ready) return;
    if (!user) nav({ to: "/login", replace: true });
    else nav({ to: user.role === "master" ? "/master/board" : "/home", replace: true });
  }, [ready, user, nav]);
  return (
    <div className="grid min-h-dvh place-items-center">
      <Logo className="animate-pulse" />
    </div>
  );
}
