/** Product rules from the brief. Covered by src/test/rules.test.ts. */
export const MAX_RECORDING_SECONDS = 60;
export const MAX_PHOTOS = 3;
export const MIN_CREW_FOR_MOOD_TREND = 5;

export const addPhotos = <T,>(current: T[], incoming: T[]): T[] =>
  [...current, ...incoming].slice(0, MAX_PHOTOS);

export const severityTone = (s: number) => (s <= 2 ? "low" : s === 3 ? "mid" : "high") as "low" | "mid" | "high";
