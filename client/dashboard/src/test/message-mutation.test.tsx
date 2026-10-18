import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useSendMessage } from "@/hooks/use-tickets";
import { qk } from "@/hooks/query-keys";
import * as api from "@/api/endpoints/messages";

vi.mock("@/api/endpoints/messages", () => ({ sendMessage: vi.fn(), listMessages: vi.fn() }));

describe("Reply delivery", () => {
  it("replaces the optimistic reply with the returned message exactly once", async () => {
    const qc = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
    qc.setQueryData(qk.messages("t1"), []);
    vi.mocked(api.sendMessage).mockResolvedValue({ id: "m1", ticket_id: "t1", sender: "shore", body: "Inspect hose", created_at: "2026-10-17T00:00:00Z" });
    const { result } = renderHook(() => useSendMessage("t1", "Reviewer"), { wrapper: ({ children }) => <QueryClientProvider client={qc}>{children}</QueryClientProvider> });
    act(() => result.current.mutate("Inspect hose"));
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(qc.getQueryData(qk.messages("t1"))).toEqual([expect.objectContaining({ id: "m1", body: "Inspect hose" })]);
  });
  it("restores previous messages when sending fails", async () => {
    const qc = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
    const previous = [{ id: "m0", body: "Earlier reply" }];
    qc.setQueryData(qk.messages("t1"), previous);
    vi.mocked(api.sendMessage).mockRejectedValue(new Error("Offline"));
    const { result } = renderHook(() => useSendMessage("t1", "Reviewer"), { wrapper: ({ children }) => <QueryClientProvider client={qc}>{children}</QueryClientProvider> });
    act(() => result.current.mutate("Inspect hose"));
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(qc.getQueryData(qk.messages("t1"))).toEqual(previous);
  });
});