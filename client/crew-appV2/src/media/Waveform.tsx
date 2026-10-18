export function Waveform({ levels, active }: { levels: number[]; active: boolean }) {
  const bars = Array.from({ length: 48 }, (_, i) => levels[levels.length - 48 + i] ?? 0);
  return (
    <div className="flex h-12 items-center justify-center gap-[3px]" aria-hidden>
      {bars.map((v, i) => (
        <span
          key={i}
          className={`w-[3px] rounded-full transition-[height] duration-75 ${active ? "bg-primary" : "bg-border"}`}
          style={{ height: `${Math.max(4, v * 48)}px` }}
        />
      ))}
    </div>
  );
}
