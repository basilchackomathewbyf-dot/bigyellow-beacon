import { useSyncExternalStore } from "react";
import { TOKEN_KEY, USER_KEY } from "@/api/config";
import type { User } from "@/api/types";

type State = { token: string | null; user: User | null; ready: boolean };
let state: State = { token: null, user: null, ready: false };
const listeners = new Set<() => void>();
const emit = () => listeners.forEach((l) => l());

function hydrate() {
  if (state.ready || typeof window === "undefined") return;
  try {
    const token = localStorage.getItem(TOKEN_KEY);
    const raw = localStorage.getItem(USER_KEY);
    state = { token, user: raw ? (JSON.parse(raw) as User) : null, ready: true };
  } catch {
    state = { token: null, user: null, ready: true };
  }
}

export const authStore = {
  getToken: () => {
    hydrate();
    return state.token;
  },
  getUser: () => {
    hydrate();
    return state.user;
  },
  set(token: string, user: User) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
    state = { token, user, ready: true };
    emit();
  },
  clear() {
    if (typeof window !== "undefined") {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
    }
    state = { token: null, user: null, ready: true };
    emit();
  },
  subscribe(l: () => void) {
    listeners.add(l);
    return () => listeners.delete(l);
  },
};

const serverSnapshot: State = { token: null, user: null, ready: false };

/** Auth state; `ready` is false during SSR and the first client render. */
export function useAuth() {
  return useSyncExternalStore(
    authStore.subscribe,
    () => {
      hydrate();
      return state;
    },
    () => serverSnapshot,
  );
}
