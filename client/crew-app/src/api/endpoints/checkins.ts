import { USE_MOCK } from "../config";
import { api } from "../client";
import { events } from "../events";
import { ApiError, type CheckinEntry, type CheckinHistory, type CheckinStartInput, type CheckinStartResult, type CheckinTag, type CheckinTurnResult } from "../types";
import { getDb } from "../mock/db";
import { id, latency, nowIso, todayKey } from "../mock/util";

const today = () => getDb().checkins.find((c) => c.date === todayKey());

/** True if today's check-in exists (GET via history in real API). */
export async function todayDone(): Promise<boolean> {
  if (!USE_MOCK) return (await api<{ done: boolean }>("GET", "/checkins/today")).done;
  return latency(() => !!today());
}

// POST /checkins  (409 if already done today)
export async function startCheckin(input: CheckinStartInput): Promise<CheckinStartResult> {
  if (!USE_MOCK) return api("POST", "/checkins", input);
  return latency(() => {
    const db = getDb();
    if (today()) throw new ApiError(409, "Already checked in today");
    if (input.mode === "quick") {
      db.checkins.push({
        date: todayKey(), mood: input.mood, fatigue: input.fatigue ?? 3, workload: 3,
        sleep_hours: input.sleep_hours ?? 7, tags: input.tags ?? [],
      });
      return { id: id("ci"), done: true };
    }
    const cid = id("ci");
    db.activeCheckin = { id: cid, turns: 0, mood: input.mood };
    const prompts = ["Thanks. What's been on your mind today?", "Thanks for sharing. How was your last sleep?"];
    return { id: cid, done: false, prompt: prompts[input.mood % 2] };
  });
}

const tips = [
  "Try a 10-minute walk on deck in daylight before your next watch.",
  "Drink a glass of water and stretch your shoulders for two minutes.",
  "If the link is up, a short call home can help.",
];

// POST /checkins/{id}/turn
export async function checkinTurn(cid: string, text: string): Promise<CheckinTurnResult> {
  if (!USE_MOCK) return api("POST", `/checkins/${cid}/turn`, { text });
  return latency(() => {
    const db = getDb();
    const a = db.activeCheckin;
    if (!a || a.id !== cid) throw new ApiError(404, "No active check-in");
    if (/test crisis/i.test(text)) return { reply: "", done: true, rail_hit: true };
    a.turns++;
    if (a.turns === 1) return { reply: "That makes sense. Has work or rest felt heavier than usual this week?", done: false };
    const mood = a.mood as CheckinEntry["mood"];
    db.checkins.push({ date: todayKey(), mood, fatigue: (6 - mood) as CheckinEntry["fatigue"], workload: 3, sleep_hours: 6.5, tags: [] });
    db.activeCheckin = null;
    return {
      reply: `Thank you for checking in — it takes strength to be honest. ${tips[mood % tips.length]}`,
      done: true,
      scores: { mood, fatigue: 6 - mood },
    };
  });
}

// POST /api/v1/checkins/{id}/welfare-request
export async function welfareRequest(cid: string): Promise<{ ok: true; welfare_id?: string; message?: string }> {
  if (!USE_MOCK) return api("POST", `/api/v1/checkins/${cid}/welfare-request`, { consent: true });
  const w = await latency(() => {
    const db = getDb();
    const req = { id: id("w"), name: db.user?.name ?? "Crew member", created_at: nowIso(), status: "pending" as const };
    db.welfare.push(req);
    return req;
  });
  events.emit("welfare.request", w);
  return { ok: true };
}

// GET /checkins/history?range=7d|30d|90d
export async function history(range: "7d" | "30d" | "90d"): Promise<CheckinHistory> {
  if (!USE_MOCK) return api("GET", `/checkins/history?range=${range}`);
  return latency(() => {
    const days = parseInt(range);
    const cutoff = new Date(Date.now() - days * 86_400_000).toISOString().slice(0, 10);
    const entries = getDb().checkins.filter((c) => c.date > cutoff).sort((a, b) => a.date.localeCompare(b.date));
    let streak = 0;
    for (let i = 0; ; i++) {
      const k = new Date(Date.now() - i * 86_400_000).toISOString().slice(0, 10);
      if (getDb().checkins.some((c) => c.date === k)) streak++;
      else if (i > 0) break;
    }
    const counts = new Map<CheckinTag, number>();
    entries.forEach((e) => e.tags.forEach((t) => counts.set(t, (counts.get(t) ?? 0) + 1)));
    const top_tags = [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 3).map(([tag, count]) => ({ tag, count }));
    const low = entries.filter((e) => e.sleep_hours < 6), ok = entries.filter((e) => e.sleep_hours >= 6);
    const avg = (xs: CheckinEntry[]) => xs.reduce((s, e) => s + e.mood, 0) / Math.max(1, xs.length);
    const insight = low.length > 2 && avg(low) < avg(ok)
      ? "Your mood is lower on days with under 6 hours of sleep."
      : "Your mood has been fairly steady. Keep protecting your rest.";
    return { entries, streak, top_tags, insight };
  });
}

// DELETE /checkins/history
export async function deleteHistory(): Promise<void> {
  if (!USE_MOCK) return api("DELETE", "/checkins/history");
  return latency(() => { getDb().checkins = []; });
}

// POST /checkins/{id}/voice (multipart: audio) -> {text}
export async function transcribeTurn(cid: string, audio: Blob): Promise<{ text: string }> {
  if (!USE_MOCK) {
    const fd = new FormData();
    fd.append("audio", audio, "turn.webm");
    return api("POST", `/checkins/${cid}/voice`, fd);
  }
  const samples = ["A bit tired, the night watches are long.", "Okay overall, missing home a little.", "Work has been heavy since the last port."];
  return latency(() => ({ text: samples[Math.floor(Math.random() * samples.length)] }));
}
