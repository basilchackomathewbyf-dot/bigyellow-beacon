import { formatDistanceToNowStrict, format } from "date-fns";

export const relTime = (iso: string) => formatDistanceToNowStrict(new Date(iso), { addSuffix: true });
export const dateTime = (iso: string) => format(new Date(iso), "d MMM, HH:mm");
export const shortDate = (iso: string) => format(new Date(iso), "d MMM yyyy");
export const bytes = (n: number) => (n >= 1024 * 1024 ? `${(n / 1024 / 1024).toFixed(1)} MB` : `${Math.round(n / 1024)} KB`);
export const pct = (n: number) => `${Math.round(n * 100)}%`;
