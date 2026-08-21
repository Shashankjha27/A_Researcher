import { useState } from "react"

import { useClaim, useOverrideVerdict } from "@/api/hooks"
import type { Verdict } from "@/api/types"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { VerdictBadge } from "@/components/VerdictBadge"

const VERDICT_OPTIONS: Verdict[] = [
  "supported",
  "provisionally_supported",
  "contradicted",
  "conflicting",
  "insufficient",
]

export function OverrideCard({ claimId }: { claimId: string }) {
  const { data } = useClaim(claimId)
  const override = data?.claim.override ?? null

  const [verdict, setVerdict] = useState<string>("")
  const [note, setNote] = useState("")
  const overrideMutation = useOverrideVerdict(claimId)

  const handleSave = () => {
    if (!verdict) {
      return
    }

    overrideMutation.mutate(
      { verdict, note: note || undefined },
      {
        onSuccess: () => {
          setVerdict("")
          setNote("")
        },
      },
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Human review</CardTitle>
      </CardHeader>

      <CardContent className="space-y-4">
        {override ? (
          <div className="rounded-lg border-l-4 border-violet-400 bg-violet-50 p-3 dark:bg-violet-500/10">
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <span className="font-semibold">Overridden:</span>

              <VerdictBadge verdict={override.overridden_verdict} />

              {override.original_verdict ? (
                <span className="text-muted-foreground">
                  (was {override.original_verdict.replace(/_/g, " ")})
                </span>
              ) : null}
            </div>

            {override.note ? (
              <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
                {override.note}
              </p>
            ) : null}
          </div>
        ) : null}

        <div className="flex flex-wrap items-center gap-2">
          <Select value={verdict} onValueChange={setVerdict}>
            <SelectTrigger className="w-56">
              <SelectValue placeholder="Corrected verdict…" />
            </SelectTrigger>

            <SelectContent>
              {VERDICT_OPTIONS.map((option) => (
                <SelectItem key={option} value={option}>
                  {option.replace(/_/g, " ")}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Input
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder="Why? (optional)"
            className="w-64"
          />

          <Button
            size="sm"
            disabled={!verdict || overrideMutation.isPending}
            onClick={handleSave}
          >
            {overrideMutation.isPending ? "Saving…" : "Save override"}
          </Button>
        </div>

        {overrideMutation.isError ? (
          <p className="text-sm text-red-600">
            Failed to save override:{" "}
            {overrideMutation.error instanceof Error
              ? overrideMutation.error.message
              : "unknown error"}
          </p>
        ) : null}
      </CardContent>
    </Card>
  )
}
