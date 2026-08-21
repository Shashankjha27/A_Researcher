import { Link, useParams } from "react-router"

import { useClaim } from "@/api/hooks"
import type { Relation } from "@/api/types"
import { ConfidenceBars } from "@/components/ConfidenceBars"
import { DebateCard } from "@/components/DebateCard"
import { FlagCard } from "@/components/FlagCard"
import { OverrideCard } from "@/components/OverrideCard"
import { VerdictLegend } from "@/components/VerdictLegend"
import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

const RELATION_STYLES: Record<Relation, string> = {
  contradiction: "bg-red-100 text-red-800",
  support: "bg-emerald-100 text-emerald-800",
  neutral: "bg-gray-100 text-gray-600",
}

export function ClaimPage() {
  const { paperId = "", claimId = "" } = useParams()
  const { data, isLoading, isError, error } = useClaim(claimId)

  if (isLoading) {
    return (
      <div className="mx-auto max-w-4xl space-y-6">
        <div className="flex items-center justify-between gap-4">
          <Skeleton className="h-6 w-64" />

          <Skeleton className="h-4 w-24" />
        </div>

        <Card>
          <CardContent className="space-y-3 pt-6">
            <Skeleton className="h-5 w-full" />

            <Skeleton className="h-5 w-4/5" />

            <div className="flex gap-2 pt-2">
              <Skeleton className="h-5 w-20" />

              <Skeleton className="h-5 w-24" />

              <Skeleton className="h-5 w-16" />
            </div>

            <Skeleton className="h-16 w-full" />
          </CardContent>
        </Card>

        <Skeleton className="h-40 w-full" />
      </div>
    )
  }

  if (isError || !data) {
    return (
      <p className="text-sm text-red-600">
        Failed to load claim:{" "}
        {error instanceof Error ? error.message : "unknown error"}
      </p>
    )
  }

  const { claim, linked_verdicts } = data

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="flex items-center justify-between gap-4">
        <h1 className="font-mono text-lg font-bold">{claim.claim_id}</h1>

        <Link
          to={`/reports/${paperId}`}
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          ← Paper report
        </Link>
      </div>

      <VerdictLegend />

      <Card>
        <CardContent className="space-y-4 pt-6">
          <p className="text-lg leading-relaxed">{claim.claim_text}</p>

          <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
            {claim.method_type ? (
              <span className="rounded bg-muted px-2 py-0.5">
                {claim.method_type}
              </span>
            ) : null}

            {claim.effect_direction ? (
              <span className="rounded bg-muted px-2 py-0.5">
                effect: {claim.effect_direction}
              </span>
            ) : null}

            {claim.sample_size != null ? (
              <span className="rounded bg-muted px-2 py-0.5">
                n={claim.sample_size}
              </span>
            ) : null}

            <span className="rounded bg-muted px-2 py-0.5">
              paper: {claim.paper_id}
            </span>
          </div>

          {"source_sentence" in claim && claim.source_sentence ? (
            <div>
              <blockquote className="border-l-4 border-amber-400 bg-amber-50 p-3 text-sm leading-relaxed dark:bg-amber-500/10">
                {claim.source_sentence}
              </blockquote>

              <Link
                to={`/papers/${paperId}/view?claim=${claim.claim_id}`}
                className="mt-1 inline-block text-xs font-semibold text-primary hover:underline"
              >
                View in paper →
              </Link>
            </div>
          ) : null}

          {claim.confidence_score != null ? (
            <div>
              <p className="text-xs font-semibold uppercase text-muted-foreground">
                Confidence
              </p>

              <p className="text-2xl font-bold">
                {claim.confidence_score.toFixed(3)}
              </p>

              <ConfidenceBars components={claim.confidence_components} />
            </div>
          ) : null}

          {(claim.flags ?? []).map((flag, index) => (
            <FlagCard key={index} flag={flag} />
          ))}
        </CardContent>
      </Card>

      <DebateCard claimId={claim.claim_id} />

      <OverrideCard claimId={claim.claim_id} />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Linked verdicts ({linked_verdicts.length})
          </CardTitle>
        </CardHeader>

        <CardContent>
          {linked_verdicts.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No pair verdicts involve this claim.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Pair</TableHead>

                  <TableHead>Relation</TableHead>

                  <TableHead>NLI prob</TableHead>

                  <TableHead>Model</TableHead>

                  <TableHead />
                </TableRow>
              </TableHeader>

              <TableBody>
                {linked_verdicts.map((verdict) => {
                  const otherId =
                    verdict.claim_id_a === claim.claim_id
                      ? verdict.claim_id_b
                      : verdict.claim_id_a

                  return (
                    <TableRow key={verdict.pair_id}>
                      <TableCell className="font-mono text-xs">
                        {verdict.pair_id}
                      </TableCell>

                      <TableCell>
                        <Badge
                          className={`border-transparent uppercase ${
                            RELATION_STYLES[verdict.relation] ??
                            RELATION_STYLES.neutral
                          }`}
                        >
                          {verdict.relation}
                        </Badge>
                      </TableCell>

                      <TableCell className="font-mono text-xs">
                        {verdict.nli_probability.toFixed(3)}
                      </TableCell>

                      <TableCell className="max-w-40 truncate text-xs text-muted-foreground">
                        {verdict.nli_model}
                      </TableCell>

                      <TableCell className="text-right">
                        <Link
                          to={`/reports/${paperId}/claims/${otherId}`}
                          className="text-xs font-semibold text-primary hover:underline"
                        >
                          {otherId} →
                        </Link>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
