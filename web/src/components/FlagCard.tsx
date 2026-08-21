import { useFlagReview } from "@/api/hooks"
import type { FlagItem } from "@/api/types"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

const SEVERITY_STYLES: Record<string, string> = {
  low: "bg-yellow-100 text-yellow-800",
  medium: "bg-amber-100 text-amber-800",
  high: "bg-red-100 text-red-800",
}

export function FlagCard({ flag }: { flag: FlagItem }) {
  const severity = flag.severity ?? "medium"

  const flagId =
    typeof flag.flag_id === "string" ? flag.flag_id : undefined

  const reviewMutation = useFlagReview()

  return (
    <div className="rounded-lg border-l-4 border-amber-400 bg-amber-50 p-3">
      <div className="mb-1 flex items-center gap-2">
        <strong className="text-sm">{flag.flag_type ?? "flag"}</strong>

        <Badge
          className={cn(
            "border-transparent uppercase",
            SEVERITY_STYLES[severity] ?? SEVERITY_STYLES.medium,
          )}
        >
          {severity}
        </Badge>
      </div>

      {flag.rationale_string ? (
        <p className="text-sm leading-relaxed text-muted-foreground">
          {flag.rationale_string}
        </p>
      ) : null}

      {flagId ? (
        <div className="mt-2 flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled={reviewMutation.isPending}
            onClick={() =>
              reviewMutation.mutate({ flagId, accepted: true })
            }
          >
            Accept
          </Button>

          <Button
            size="sm"
            variant="ghost"
            disabled={reviewMutation.isPending}
            onClick={() =>
              reviewMutation.mutate({ flagId, accepted: false })
            }
          >
            Dismiss
          </Button>

          {reviewMutation.isSuccess ? (
            <span className="text-xs text-muted-foreground">
              Review saved.
            </span>
          ) : null}

          {reviewMutation.isError ? (
            <span className="text-xs text-red-600">
              Failed to save review.
            </span>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
