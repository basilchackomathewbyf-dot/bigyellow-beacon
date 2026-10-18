import type { TicketFilters } from "@/api/types";

export const qk = {
  tickets: {
    all: ["tickets"] as const,
    list: (f: TicketFilters) => ["tickets", "list", f] as const,
    detail: (id: string) => ["tickets", "detail", id] as const,
    similar: (id: string) => ["tickets", "similar", id] as const,
  },
  analysis: (id: string) => ["analysis", id] as const,
  messages: (id: string) => ["messages", id] as const,
  learnings: { all: ["learnings"] as const, detail: (id: string) => ["learnings", id] as const },
  fleet: { overview: ["fleet", "overview"] as const, clusters: ["fleet", "clusters"] as const },
  vessels: ["vessels"] as const,
};
