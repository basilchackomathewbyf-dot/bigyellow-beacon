import { createFileRoute, Outlet, Navigate } from "@tanstack/react-router";
import { useSession } from "@/lib/session";

export const Route = createFileRoute("/_app/master")({ component: MasterLayout });

function MasterLayout() {
  const { user } = useSession();
  if (user?.role !== "master") return <Navigate to="/home" replace />;
  return <Outlet />;
}
