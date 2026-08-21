import type { Verdict } from "@/api/types"
import { VerdictBadge } from "@/components/VerdictBadge"
import { cn } from "@/lib/utils"

const VERDICTS: Verdict[] = [
  "supported",
  "provisionally_supported",
  "contradicted",
  "conflicting",
  "insufficient",
]

export function VerdictLegend({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-x-3 gap-y-1.5",
        className,
      )}
      aria-label="Verdict color legend"
    >
      {VERDICTS.map((verdict) => (
        <span key={verdict} className="flex items-center">
          <VerdictBadge verdict={verdict} />
        </span>
      ))}
    </div>
  )
}
