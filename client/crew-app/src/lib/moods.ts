import { Cloud, CloudRain, CloudSun, Sun, SunDim, type LucideIcon } from "lucide-react";

/** Sky icons for the 1-5 mood scale: always render, unlike emoji on older ship devices. */
export const moodBg = ["", "bg-mood-1", "bg-mood-2", "bg-mood-3", "bg-mood-4", "bg-mood-5"];
export const moodIcon: Record<number, LucideIcon> = { 1: CloudRain, 2: Cloud, 3: CloudSun, 4: SunDim, 5: Sun };
