import type React from "react";
import { useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import type { User } from "@/api/types";
import { restoreMockSession, me } from "@/api/endpoints/auth";
import { setAuthToken } from "@/api/client";
import i18n from "@/i18n";

interface Session { user: User | null; ready: boolean; signIn: (u: User, token: string) => void; signOut: () => void; update: (u: User) => void }
// Keep one context instance across hot reloads so a re-evaluated module doesn't orphan the provider.
const g = globalThis as unknown as { __beaconSessionCtx?: React.Context<Session | null> };
const Ctx = (g.__beaconSessionCtx ??= createContext<Session | null>(null));
const KEY = "beacon.session";

export function SessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const qc = useQueryClient();

  const signOut = useCallback(() => {
    void qc.cancelQueries();
    qc.clear();
    localStorage.removeItem(KEY);
    setAuthToken(null);
    setUser(null);
  }, [qc]);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(KEY);
      if (raw) {
        const { user: u, token } = JSON.parse(raw) as { user: User; token: string };
        restoreMockSession(u);
        setAuthToken(token);
        setUser(u);
        void i18n.changeLanguage(u.language);

        // Actively verify and hydrate from GET /api/v1/me
        me()
          .then((freshUser) => {
            setUser(freshUser);
            localStorage.setItem(KEY, JSON.stringify({ user: freshUser, token }));
            if (freshUser.language && freshUser.language !== u.language) {
              void i18n.changeLanguage(freshUser.language);
            }
          })
          .catch((err: unknown) => {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const status = (err as any)?.status;
            if (status === 401) {
              signOut();
            }
          });
      }
    } catch { /* ignore */ }
    setReady(true);
  }, [signOut]);

  const signIn = useCallback((u: User, token: string) => {
    localStorage.setItem(KEY, JSON.stringify({ user: u, token }));
    setAuthToken(token);
    setUser(u);
    void i18n.changeLanguage(u.language);
  }, []);
  const update = useCallback((u: User) => {
    const raw = localStorage.getItem(KEY);
    const token = raw ? JSON.parse(raw).token : "";
    localStorage.setItem(KEY, JSON.stringify({ user: u, token }));
    setUser(u);
  }, []);

  return <Ctx.Provider value={{ user, ready, signIn, signOut, update }}>{children}</Ctx.Provider>;
}

export function useSession() {
  const s = useContext(Ctx);
  if (!s) throw new Error("useSession outside SessionProvider");
  return s;
}
