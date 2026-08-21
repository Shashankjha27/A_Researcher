import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import type { Verdict } from "@/api/types"

const VERDICT_STYLES: Record<Verdict, string> = {
  supported: "bg-emerald-100 text-emerald-800",
  provisionally_supported: "bg-teal-100 text-teal-800",
  contradicted: "bg-red-100 text-red-800",
  conflicting: "bg-orange-100 text-orange-800",
  insufficient: "bg-gray-100 text-gray-600",
}

const VERDICT_LABELS: Record<Verdict, string> = {
  supported: "Supported",
  provisionally_supported: "Provisionally supported",
  contradicted: "Contradicted",
  conflicting: "Conflicting evidence",
  insufficient: "Insufficient",
}

export function VerdictBadge({ verdict }: { verdict: Verdict }) {
  return (
    <Badge
      className={cn(
        "border-transparent uppercase",
        VERDICT_STYLES[verdict] ?? VERDICT_STYLES.insufficient,
      )}
    >
      {VERDICT_LABELS[verdict] ?? verdict}
    </Badge>
  )
}
