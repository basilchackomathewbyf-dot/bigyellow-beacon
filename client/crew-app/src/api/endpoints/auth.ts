import { USE_MOCK } from "../config";
import { api, setAuthToken } from "../client";
import { ApiError, type Language, type User, type PairDevicePayload, type PairDeviceResponse } from "../types";
import { getDb } from "../mock/db";
import { CREW } from "../mock/seed";
import { latency } from "../mock/util";

const DEVICE_TOKEN_KEY = "beacon.device_token";
const PAIRED_DEVICE_KEY = "beacon.paired_device";
const LAST_CREW_KEY = "beacon.last_crew";

export interface LastCrewInfo {
  id: string;
  name: string;
  department?: string;
  rank?: string;
  vessel?: string;
}

export const getStoredDeviceToken = (): string | null => {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(DEVICE_TOKEN_KEY);
};

export const setStoredDeviceToken = (token: string | null) => {
  if (typeof window === "undefined") return;
  if (token) localStorage.setItem(DEVICE_TOKEN_KEY, token);
  else localStorage.removeItem(DEVICE_TOKEN_KEY);
};

export const getStoredPairedInfo = (): PairDeviceResponse | null => {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(PAIRED_DEVICE_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    if (parsed && (parsed.crew_name === "Arjun Nair" || !parsed.crew_name)) {
      parsed.crew_name = "Amarjeet";
    }
    return parsed;
  } catch {
    return null;
  }
};

export const setStoredPairedInfo = (info: PairDeviceResponse | null) => {
  if (typeof window === "undefined") return;
  if (info) {
    if (info.crew_name === "Arjun Nair") info.crew_name = "Amarjeet";
    localStorage.setItem(PAIRED_DEVICE_KEY, JSON.stringify(info));
  } else {
    localStorage.removeItem(PAIRED_DEVICE_KEY);
  }
};

export const getStoredLastCrew = (): LastCrewInfo | null => {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(LAST_CREW_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    if (parsed && parsed.name === "Arjun Nair") {
      parsed.name = "Amarjeet";
    }
    return parsed;
  } catch {
    return null;
  }
};

export const setStoredLastCrew = (info: LastCrewInfo | null) => {
  if (typeof window === "undefined") return;
  if (info) {
    if (info.name === "Arjun Nair") info.name = "Amarjeet";
    localStorage.setItem(LAST_CREW_KEY, JSON.stringify(info));
  } else {
    localStorage.removeItem(LAST_CREW_KEY);
  }
};

/** Helper to resolve crew user dynamically by crew ID or name */
export function resolveCrewUser(crewId?: string, crewName?: string): User {
  if (crewName === "Arjun Nair") crewName = "Amarjeet";
  if (crewId) {
    const found = CREW.find(
      (c) =>
        c.id.toLowerCase() === crewId.toLowerCase() ||
        c.id.toLowerCase() === `u-${crewId.toLowerCase()}` ||
        c.name.toLowerCase() === crewId.toLowerCase()
    );
    if (found) {
      const nm = crewName?.trim() || found.name;
      return { ...found, name: nm === "Arjun Nair" ? "Amarjeet" : nm };
    }
  }
  const isUuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(crewId || "");
  const clean = isUuid ? "" : (crewId || "").replace(/^(u|user)[-_]/i, "").replace(/[-_]/g, " ").trim();
  const formattedName =
    crewName?.trim() ||
    (isUuid && (crewId || "").toLowerCase().startsWith("01a14acb")
      ? "Amarjeet"
      : clean
        ? clean.replace(/\b\w/g, (l) => l.toUpperCase())
        : "Amarjeet");
  const isMaster = (crewId || "").toLowerCase().includes("master");
  const finalName = isMaster ? "Capt. Kundan" : (formattedName === "Arjun Nair" ? "Amarjeet" : formattedName);
  return {
    id: crewId || "01a14acb-e04c-79f8-aa4e-0395dcf068d0",
    name: finalName,
    rank: isMaster ? "Master" : "AB Seaman",
    rank_band: isMaster ? "officer" : "rating",
    role: isMaster ? "master" : "crew",
    language: "en",
    vessel: "MV Pacific Star",
  };
}

/** Demo accounts used while USE_MOCK is true or for quick sign-in. */
export const DEMO_ACCOUNTS = [
  { username: "amarjeet", password: "crew123", userId: "01a14acb-e04c-79f8-aa4e-0395dcf068d0", label: "Amarjeet (AB Seaman)" },
  { username: "crew", password: "crew123", userId: "01a14acb-e04c-79f8-aa4e-0395dcf068d0", label: "Amarjeet (AB Seaman)" },
  { username: "master", password: "master123", userId: "u-master", label: "Capt. Kundan (Master)" },
  { username: "jose", password: "crew123", userId: "u-3", label: "Jose Santos (Bosun)" },
  { username: "olena", password: "crew123", userId: "u-4", label: "Olena Kovalenko (2nd Officer)" },
  { username: "mark", password: "crew123", userId: "u-5", label: "Mark Dela Cruz (Oiler)" },
  { username: "priya", password: "crew123", userId: "u-6", label: "Priya Sharma (3rd Engineer)" },
  { username: "taras", password: "crew123", userId: "u-7", label: "Taras Melnyk (Chief Engineer)" },
  { username: "ramon", password: "crew123", userId: "u-8", label: "Ramon Bautista (Cook)" },
] as const;

// POST /api/v1/auth/pair {pairing_code, crew_id, department, crew_name, pin} -> PairDeviceResponse
export async function pairDevice(payload: PairDevicePayload): Promise<PairDeviceResponse> {
  if (!USE_MOCK) {
    const res = await api<PairDeviceResponse>("POST", "/api/v1/auth/pair", payload);
    setStoredDeviceToken(res.device_token);
    setStoredPairedInfo(res);
    setStoredLastCrew({ id: res.crew_id || "01a14acb-e04c-79f8-aa4e-0395dcf068d0", name: res.crew_name || "Amarjeet", department: res.department, vessel: res.vessel_id });
    return res;
  }
  return latency(() => {
    const user = resolveCrewUser(payload.crew_id, payload.crew_name);
    const devToken = `dev_mock_${Date.now()}`;
    const res: PairDeviceResponse = {
      device_token: devToken,
      device_id: `d-${Date.now()}`,
      vessel_id: "MV-PACIFIC-STAR",
      crew_id: user.id,
      crew_name: payload.crew_name || user.name,
      department: payload.department || "Deck",
      expires_at: new Date(Date.now() + 90 * 86400000).toISOString(),
      token: devToken,
    };
    setStoredDeviceToken(devToken);
    setStoredPairedInfo(res);
    setStoredLastCrew({ id: user.id, name: user.name, department: res.department, rank: user.rank, vessel: res.vessel_id });
    return res;
  });
}

// POST /api/v1/auth/login with device_token + pin -> {token, user}
export async function loginWithDevice(device_token: string, pin: string = "1234"): Promise<{ token: string; user: User }> {
  if (!USE_MOCK) {
    const r = await api<{ token: string; user: User }>("POST", "/api/v1/auth/login", { device_token, pin });
    setAuthToken(r.token);
    setStoredLastCrew({ id: r.user.id, name: r.user.name, department: (r.user as any).department || "Deck", rank: r.user.rank, vessel: r.user.vessel });
    return r;
  }
  return latency(() => {
    const paired = getStoredPairedInfo();
    const last = getStoredLastCrew();
    const user = resolveCrewUser(last?.id || paired?.crew_id, last?.name || paired?.crew_name);
    getDb().user = { ...user };
    const token = `tok-${user.id}`;
    setAuthToken(token);
    setStoredLastCrew({ id: user.id, name: user.name, department: (user as any).department || "Deck", rank: user.rank, vessel: user.vessel });
    return { token, user: getDb().user! };
  });
}

// POST /api/v1/auth/login {username, password} -> {token, user}
export async function login(username: string, password: string): Promise<{ token: string; user: User }> {
  if (!USE_MOCK) {
    const r = await api<{ token: string; user: User }>("POST", "/api/v1/auth/login", { username, password });
    setAuthToken(r.token);
    setStoredLastCrew({ id: r.user.id, name: r.user.name, department: (r.user as any).department || "Deck", rank: r.user.rank, vessel: r.user.vessel });
    return r;
  }
  return latency(() => {
    const clean = username.trim().toLowerCase();
    const acc = DEMO_ACCOUNTS.find((a) => a.username === clean);
    if (acc) {
      if (acc.password !== password) {
        throw new ApiError(401, "Wrong username or password");
      }
      const user = resolveCrewUser(acc.userId);
      getDb().user = { ...user };
      const token = `tok-${user.id}`;
      setAuthToken(token);
      setStoredLastCrew({ id: user.id, name: user.name, department: (user as any).department || "Deck", rank: user.rank, vessel: user.vessel });
      return { token, user: getDb().user! };
    }
    if (!password || password === "nope" || password.trim().length < 4) {
      throw new ApiError(401, "Wrong username or password");
    }
    const user = resolveCrewUser(clean);
    getDb().user = { ...user };
    const token = `tok-${user.id}`;
    setAuthToken(token);
    setStoredLastCrew({ id: user.id, name: user.name, department: (user as any).department || "Deck", rank: user.rank, vessel: user.vessel });
    return { token, user: getDb().user! };
  });
}

// GET /api/v1/me
export async function me(): Promise<User> {
  if (!USE_MOCK) return api("GET", "/api/v1/me");
  return latency(() => {
    const u = getDb().user;
    if (!u) throw new ApiError(401, "Not signed in");
    return u;
  });
}

/** Mock-only: restore a session after page reload. */
export function restoreMockSession(user: User) {
  if (USE_MOCK) getDb().user = user;
  setAuthToken(`tok-${user.id}`);
}

// PUT /api/v1/me/preferences
export async function updatePreferences(p: { language?: Language; checkin_reminder_at?: string }): Promise<User> {
  if (!USE_MOCK) return api("PUT", "/api/v1/me/preferences", p);
  return latency(() => {
    const db = getDb();
    db.user = { ...db.user!, ...p };
    return db.user;
  });
}
