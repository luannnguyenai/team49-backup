import Link from "next/link";
import { Brain } from "lucide-react";

import { cn } from "@/lib/utils";

interface BrandLogoProps {
  compact?: boolean;
  subtitle?: string | null;
  href?: string;
  className?: string;
}

export default function BrandLogo({
  compact = false,
  subtitle = null,
  href = "/",
  className,
}: BrandLogoProps) {
  return (
    <Link href={href} className={cn("flex shrink-0 items-center gap-3", className)}>
      <div
        className={cn(
          "flex items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-600 via-cyan-500 to-teal-400 text-white shadow-lg shadow-cyan-500/20",
          compact ? "h-8 w-8 rounded-lg" : "h-10 w-10",
        )}
      >
        <Brain className={compact ? "h-4 w-4" : "h-5 w-5"} />
      </div>
      <div>
        <p className="text-sm font-semibold text-slate-950 dark:text-white">AI Learning Hub</p>
        {subtitle ? <p className="text-xs text-slate-500 dark:text-slate-300">{subtitle}</p> : null}
      </div>
    </Link>
  );
}
