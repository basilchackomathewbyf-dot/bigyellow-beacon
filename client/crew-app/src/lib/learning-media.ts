/**
 * Learning Media Helper
 * Resolves images for maritime safety learnings.
 * If backend sends a valid picture, show that.
 * Otherwise, show different maritime safety images deterministically per learning.
 */

export const FALLBACK_LEARNING_IMAGES = [
  "https://images.unsplash.com/photo-1572883454114-1cf0031ede2a?w=1000&q=80", // Deck machinery & winch safety
  "https://images.unsplash.com/photo-1578575437130-527eed3abbec?w=1000&q=80", // Mooring lines & deck fittings
  "https://images.unsplash.com/photo-1500375592092-40eb2168fd21?w=1000&q=80", // Night watch & open ocean navigation
  "https://images.unsplash.com/photo-1605745341112-85968b19335b?w=1000&q=80", // Crane & container handling
  "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=1000&q=80", // Engine room valves & piping
  "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?w=1000&q=80", // Maritime safety equipment & inspection
  "https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?w=1000&q=80", // Rough weather vessel transit
  "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=1000&q=80", // Workshop electrical tools & repairs
  "https://images.unsplash.com/photo-1494412574643-ff11b0a5c1c3?w=1000&q=80", // Cargo vessel alongside quay
  "https://images.unsplash.com/photo-1508873696983-2df5293cb395?w=1000&q=80", // Enclosed space tank entry & safety
];

/**
 * Deterministically returns a different fallback image based on the learning ID or key.
 */
export function getFallbackImageForLearning(key?: string): string {
  if (!key) return FALLBACK_LEARNING_IMAGES[0];
  let hash = 0;
  for (let i = 0; i < key.length; i++) {
    hash = (hash << 5) - hash + key.charCodeAt(i);
    hash |= 0;
  }
  const index = Math.abs(hash) % FALLBACK_LEARNING_IMAGES.length;
  return FALLBACK_LEARNING_IMAGES[index];
}

/**
 * Returns the picture URL:
 * - If backend sends a valid picture URL, returns that URL.
 * - Else returns a distinct fallback image based on the learning ID.
 */
export function getLearningImageUrl(
  media?: { kind?: string; url?: string } | null,
  key?: string
): string {
  const url = media?.url?.trim();
  if (url && url.length > 0) {
    return url;
  }
  return getFallbackImageForLearning(key);
}
