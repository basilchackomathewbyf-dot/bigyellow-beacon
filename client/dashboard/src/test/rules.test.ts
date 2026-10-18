import { describe, expect, it } from "vitest";
import { audienceCount, canAddMedia, canShowWellbeing, canTransition, classifyFile, validateReject } from "@/lib/rules";
import { seedTickets, seedVessels } from "@/api/mock/seed";

describe("ticket transitions", () => {
  it("accept only from NEW", () => {
    expect(canTransition("accept", "NEW")).toBe(true);
    expect(canTransition("accept", "IN_REVIEW")).toBe(false);
  });
  it("close only from IN_REVIEW", () => {
    expect(canTransition("close", "IN_REVIEW")).toBe(true);
    expect(canTransition("close", "NEW")).toBe(false);
  });
  it("reject requires reason and note", () => {
    expect(validateReject("duplicate", "")).toBe(false);
    expect(validateReject(undefined, "x")).toBe(false);
    expect(validateReject("duplicate", "seen before")).toBe(true);
  });
});

describe("media rules", () => {
  it("rejects video over 6.0 s", () => {
    const r = classifyFile({ type: "video/mp4", size: 1000 }, 8.4);
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.error).toBe("Video is 8.4 s. Maximum is 6 seconds.");
  });
  it("accepts video of exactly 6.0 s", () => expect(classifyFile({ type: "video/mp4", size: 1000 }, 6).ok).toBe(true));
  it("rejects images over 5 MB", () => expect(classifyFile({ type: "image/png", size: 5 * 1024 * 1024 + 1 }).ok).toBe(false));
  it("rejects video over 20 MB", () => expect(classifyFile({ type: "video/mp4", size: 20 * 1024 * 1024 + 1 }, 3).ok).toBe(false));
  it("allows 1 primary + 2 extra images only", () => {
    expect(canAddMedia([{ kind: "video" }, { kind: "image" }], "image")).toBe(true);
    expect(canAddMedia([{ kind: "video" }, { kind: "image" }, { kind: "image" }], "image")).toBe(false);
    expect(canAddMedia([{ kind: "image" }], "video")).toBe(false);
  });
});

describe("privacy", () => {
  it("wellbeing hidden when n < 5", () => {
    expect(canShowWellbeing(4)).toBe(false);
    expect(canShowWellbeing(5)).toBe(true);
  });
  it("tickets carry no reporter identity", () => {
    const now = Date.now();
    const keys = seedTickets(now, seedVessels(now)).flatMap((t) => Object.keys(t));
    expect(keys.some((k) => /reporter/i.test(k))).toBe(false);
  });
  it("audience count", () => expect(audienceCount("selected", ["a", "b"], 6)).toBe(2));
});

import { currentFlowStep } from "@/lib/rules";
describe("review flow step", () => {
  it("NEW ticket asks to review AI then decide", () => expect(currentFlowStep("NEW", false)).toBe(1));
  it("accepted without reply asks for reply", () => expect(currentFlowStep("IN_REVIEW", false)).toBe(3));
  it("accepted with reply asks to close", () => expect(currentFlowStep("IN_REVIEW", true)).toBe(4));
  it("closed and rejected are done", () => {
    expect(currentFlowStep("CLOSED", true)).toBe(5);
    expect(currentFlowStep("REJECTED", false)).toBe(5);
  });
});
