import { describe, expect, it } from "vitest";
import { MAX_RECORDING_SECONDS, MAX_PHOTOS, addPhotos } from "@/lib/rules";
import { deleteHistory, startCheckin } from "@/api/endpoints/checkins";
import { login } from "@/api/endpoints/auth";

describe("Beacon rules", () => {
  it("caps voice recordings at 60 seconds", () => expect(MAX_RECORDING_SECONDS).toBe(60));
  it("keeps at most 3 photos", () => {
    expect(MAX_PHOTOS).toBe(3);
    expect(addPhotos([1, 2], [3, 4, 5])).toEqual([1, 2, 3]);
  });
  it("signs crew in with crew / crew123", async () => {
    expect((await login("crew", "crew123")).user.role).toBe("crew");
  });
  it("signs the Master in with master / master123", async () => {
    expect((await login("master", "master123")).user.role).toBe("master");
  });
  it("rejects a wrong password", async () => {
    await expect(login("crew", "nope")).rejects.toMatchObject({ status: 401 });
  });
  it("rejects a second check-in on the same day with 409", async () => {
    await login("crew", "crew123");
    await deleteHistory();
    await startCheckin({ mode: "quick", mood: 4 });
    await expect(startCheckin({ mode: "quick", mood: 3 })).rejects.toMatchObject({ status: 409 });
  });
  it("provides multilingual report capture keys with bold tags for mic and paperclip", async () => {
    const { default: en } = await import("@/i18n/locales/en");
    const { default: hi } = await import("@/i18n/locales/hi");

    expect(en.report.capture.greeting).toBe(
      "Hi, tell me what you saw, in any language you like. Tap the <b>mic</b> to talk, or the <b>paperclip</b> to add photos."
    );
    expect(en.report.capture.subtitle).toBe(
      "Speak or type in any language, and add photos if you like."
    );
    expect(en.report.capture.inputPlaceholder).toBe("Type in any language…");

    expect(hi.report.capture.greeting).toContain("<b>");
    expect(hi.report.capture.greeting).toContain("</b>");
    expect(hi.report.capture.subtitle.length).toBeGreaterThan(0);
    expect(hi.report.capture.inputPlaceholder.length).toBeGreaterThan(0);
  });
});
