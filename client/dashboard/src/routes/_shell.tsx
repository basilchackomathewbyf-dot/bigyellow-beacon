import { Outlet, createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth-store";
import { AppSidebar } from "@/components/beacon/app-sidebar";
import { TopBar } from "@/components/beacon/top-bar";
import { DevPanel } from "@/components/beacon/dev-panel";
import { useNewTicketWatcher } from "@/hooks/use-tickets";
import { USE_MOCK } from "@/api/config";

export const Route = createFileRoute("/_shell")({
  component: ShellLayout,
});

function ShellLayout() {
  const { user, ready } = useAuth();
  const navigate = useNavigate();
  useEffect(() => {
    if (ready && !user) navigate({ to: "/login" });
  }, [ready, user, navigate]);
  useNewTicketWatcher(ready && !!user);

  if (!ready || !user) return <div className="min-h-screen bg-background" />;

  return (
    <div className="flex min-h-screen bg-background">
      <AppSidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <main className="mx-auto w-full max-w-[1600px] flex-1 px-6 py-6 xl:px-8">
          <Outlet />
        </main>
      </div>
      {USE_MOCK && <DevPanel />}
    </div>
  );
}
