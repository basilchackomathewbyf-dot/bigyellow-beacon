// @lovable.dev/vite-tanstack-config already includes the following — do NOT add them manually
// or the app will break with duplicate plugins:
//   - TanStack devtools (dev-only, first), tanstackStart, viteReact, tailwindcss, tsConfigPaths,
//     nitro (build-only using cloudflare as a default target), VITE_* env injection, @ path alias,
//     React/TanStack dedupe, error logger plugins, and sandbox detection (port/host/strictPort).
// You can pass additional config via defineConfig({ vite: { ... }, etc... }) if needed.
import { defineConfig } from "@lovable.dev/vite-tanstack-config";

export default defineConfig({
  tanstackStart: {
    // Redirect TanStack Start's bundled server entry to src/server.ts (our SSR error wrapper).
    // nitro/vite builds from this
    server: { entry: "server" },
  },
  vite: {
    server: {
      host: true,
      allowedHosts: [
        "beacon.bigyellow.ai",
        "beacon-dashboard.bigyellow.ai",
        "beacon-ws.bigyellow.ai",
        ".bigyellow.ai",
        "35.254.60.253",
        ".sslip.io",
        "localhost",
        "127.0.0.1",
      ],
    },
    // Pre-bundle up front so the dev server never re-optimizes mid-session
    // (a late re-optimize loads two React copies -> "reading 'useState'" crash).
    optimizeDeps: {
      include: [
        "react", "react-dom", "react/jsx-runtime", "react-dom/client", "react-i18next", "i18next", "dexie", "recharts", "sonner", "zod",
        "lucide-react", "@tanstack/react-query", "class-variance-authority", "clsx", "tailwind-merge",
        "@radix-ui/react-alert-dialog", "@radix-ui/react-checkbox", "@radix-ui/react-collapsible", "@radix-ui/react-dialog",
        "@radix-ui/react-dropdown-menu", "@radix-ui/react-label", "@radix-ui/react-popover", "@radix-ui/react-progress",
        "@radix-ui/react-select", "@radix-ui/react-slider", "@radix-ui/react-slot",
      ],
    },
  },
});
