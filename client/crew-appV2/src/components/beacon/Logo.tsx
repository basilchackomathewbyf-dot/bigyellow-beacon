import logo from "@/assets/logo.png";
import { cn } from "@/lib/utils";

export function Logo({ className, size = 36 }: { className?: string; size?: number }) {
  return (
    <div className={cn("flex items-center gap-2.5", className)}>
      <img src={logo} alt="" width={size} height={size} className="drop-shadow-sm" style={{ width: size, height: size }} />
      <span className="font-display text-[17px] font-extrabold tracking-tight">
        Beacon<span className="text-sun">.</span>
      </span>
    </div>
  );
}
