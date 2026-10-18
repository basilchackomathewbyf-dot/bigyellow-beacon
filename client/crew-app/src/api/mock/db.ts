import type {
  AnchorCard, CheckinEntry, InboxItem, Learning, Message, PairedDevice, StructureResult, SyncStatus, Ticket, User, WelfareRequest,
} from "../types";
import { CREW, seedAnchors, seedCheckins, seedDevices, seedInbox, seedLearnings, seedMessages, seedTickets, seedWelfare } from "./seed";

export interface Draft {
  id: string;
  text?: string;
  audio_url?: string;
  photo_urls: string[];
  structure?: StructureResult;
}

export interface MockDb {
  user: User | null;
  tickets: Ticket[];
  messages: Message[];
  anchors: AnchorCard[];
  learnings: Learning[];
  learningAcks: Record<string, number>;
  checkins: CheckinEntry[];
  activeCheckin: { id: string; turns: number; mood: number } | null;
  inbox: InboxItem[];
  welfare: WelfareRequest[];
  devices: PairedDevice[];
  drafts: Record<string, Draft>;
  sync: SyncStatus;
  edgeReachable: boolean;
  briefVersion: number;
  ticketSeq: number;
}

let db: MockDb | null = null;

function fresh(): MockDb {
  const now = new Date().toISOString();
  return {
    user: null,
    tickets: seedTickets(),
    messages: seedMessages(),
    anchors: seedAnchors(),
    learnings: seedLearnings(),
    learningAcks: { l1: 3, l2: 5, l3: 8 },
    checkins: seedCheckins(),
    activeCheckin: null,
    inbox: seedInbox(),
    welfare: seedWelfare(),
    devices: seedDevices(),
    drafts: {},
    sync: { link: "UP", last_push_at: now, last_pull_at: now, outbox_pending: 0 },
    edgeReachable: true,
    briefVersion: 0,
    ticketSeq: 43,
  };
}

/** Lazily-built in-memory state (never at module scope: workers disallow random at import). */
export function getDb(): MockDb {
  if (!db) db = fresh();
  return db;
}

export function resetDb() {
  const user = db?.user ?? null;
  db = fresh();
  db.user = user;
}

export const crewById = (id: string) => CREW.find((c) => c.id === id);
