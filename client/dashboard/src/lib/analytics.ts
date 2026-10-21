/**
 * Google Analytics 4 (gtag) — shore dashboard.
 * Disabled when VITE_GA_MEASUREMENT_ID is empty string.
 * Never send ticket descriptions, crew names, or other PII.
 */

declare global {
  interface Window {
    dataLayer?: unknown[];
    gtag?: (...args: unknown[]) => void;
  }
}

const MEASUREMENT_ID =
  (import.meta.env.VITE_GA_MEASUREMENT_ID as string | undefined)?.trim() ||
  "G-Y55Y8236GB";

let initialized = false;

function canTrack(): boolean {
  return typeof window !== "undefined" && !!MEASUREMENT_ID && MEASUREMENT_ID.startsWith("G-");
}

export function initAnalytics(): void {
  if (!canTrack() || initialized) return;
  initialized = true;

  window.dataLayer = window.dataLayer || [];
  // Must match Google's snippet: push Arguments, not a plain array
  window.gtag = function gtag() {
    // eslint-disable-next-line prefer-rest-params
    window.dataLayer?.push(arguments);
  };
  window.gtag("js", new Date());
  // No debug_mode — those hits only appear in Admin → DebugView and are hidden from Realtime
  window.gtag("config", MEASUREMENT_ID, {
    send_page_view: false,
    anonymize_ip: true,
  });

  const script = document.createElement("script");
  script.async = true;
  script.src = `https://www.googletagmanager.com/gtag/js?id=${MEASUREMENT_ID}`;
  document.head.appendChild(script);
}

export function trackPageView(path: string, title?: string): void {
  if (!canTrack() || !window.gtag) return;
  window.gtag("event", "page_view", {
    page_path: sanitizePath(path),
    page_title: title || document.title,
  });
}

export function track(event: string, params?: Record<string, string | number | boolean | undefined>): void {
  if (!canTrack() || !window.gtag) return;
  const clean: Record<string, string | number | boolean> = {};
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v === undefined) continue;
      clean[k] = v;
    }
  }
  window.gtag("event", event, clean);
}

function sanitizePath(path: string): string {
  return path
    .replace(/\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi, "/:id")
    .replace(/\/\d+/g, "/:id");
}

export const analyticsEnabled = canTrack;
