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
});
