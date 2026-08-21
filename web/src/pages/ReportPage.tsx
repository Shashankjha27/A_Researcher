import { Link, useParams } from "react-router"

import { useReport } from "@/api/hooks"
import { ClaimCard } from "@/components/ClaimCard"
import { ContradictionCard } from "@/components/ContradictionCard"
import { FlagCard } from "@/components/FlagCard"
import { TrustLedger } from "@/components/TrustLedger"
import { VerdictLegend } from "@/components/VerdictLegend"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

export function ReportPage() {
  const { paperId = "" } = useParams()
  const { data, isLoading, isError, error } = useReport(paperId)

  if (isLoading) {
    return (
      <div className="mx-auto max-w-6xl space-y-4">
        <Skeleton className="h-8 w-72" />

        <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
          <div className="space-y-3">
            <Skeleton className="h-40 w-full" />
            <Skeleton className="h-64 w-full" />
          </div>

          <Skeleton className="h-48 w-full" />
        </div>
      </div>
    )
  }

  if (isError || !data) {
    return (
      <p className="text-sm text-red-600">
        Failed to load report:{" "}
        {error instanceof Error ? error.message : "unknown error"}
      </p>
    )
  }

  const flags = data.claims.flatMap((claim) => claim.flags ?? [])

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-bold">Verification report</h1>

        <Link
          to="/"
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          ← Library
        </Link>
      </div>

      <TrustLedger nliModel={data.nli_model} />

      <div className="grid items-start gap-6 lg:grid-cols-[1fr_320px]">
        <div className="min-w-0 space-y-6">
          {data.contradictions.length > 0 ? (
            <section className="space-y-3">
              <h2 className="text-lg font-bold">Contradictions & evidence</h2>

              {data.contradictions.map((item, index) => (
                <ContradictionCard key={item.pair_id} item={item} index={index} />
              ))}
            </section>
          ) : null}

          {data.claims.length > 0 ? (
            <section className="space-y-3">
              <h2 className="text-lg font-bold">
                Claims ({data.claims.length})
              </h2>

              <VerdictLegend />

              {data.claims.map((claim) => (
                <ClaimCard key={claim.claim_id} claim={claim} />
              ))}
            </section>
          ) : null}
        </div>

        <aside className="space-y-3">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                Flags ({flags.length})
              </CardTitle>
            </CardHeader>

            <CardContent className="space-y-2">
              {flags.length === 0 ? (
                <p className="text-sm text-muted-foreground">No flags.</p>
              ) : (
                flags.map((flag, index) => (
                  <FlagCard key={index} flag={flag} />
                ))
              )}
            </CardContent>
          </Card>
        </aside>
      </div>
    </div>
  )
}
