import { Link } from "react-router"

import type { ClaimRecord, EvidenceItem } from "@/api/types"
import { ConfidenceBars } from "@/components/ConfidenceBars"
import { FlagCard } from "@/components/FlagCard"
import { VerdictBadge } from "@/components/VerdictBadge"
import {
  Card,
  CardContent,
  CardHeader,
} from "@/components/ui/card"

function EvidenceList({
  items,
  kind,
}: {
  items: EvidenceItem[]
  kind: "supporting" | "contradicting"
}) {
  if (!items.length) {
    return null
  }

  const isSupporting = kind === "supporting"

  return (
    <div>
      <p
        className={`mb-1 text-xs font-semibold uppercase ${
          isSupporting
            ? "text-emerald-700 dark:text-emerald-400"
            : "text-red-700 dark:text-red-400"
        }`}
      >
        {isSupporting ? "Supporting" : "Contradicting"} evidence (
        {items.length})
      </p>

      <ul className="space-y-2">
        {items.map((item, index) => (
          <li
            key={index}
            className={`rounded-md border-l-4 bg-muted/50 p-3 text-sm leading-relaxed ${
              isSupporting ? "border-emerald-500" : "border-red-500"
            }`}
          >
            {item.text}

            {item.score != null ? (
              <span className="ml-2 font-mono text-xs text-muted-foreground">
                score {item.score.toFixed(3)}
              </span>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  )
}

export function ClaimCard({ claim }: { claim: ClaimRecord }) {
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <Link
          to={`/reports/${claim.paper_id}/claims/${claim.claim_id}`}
          className="font-mono text-xs text-muted-foreground hover:text-primary hover:underline"
        >
          {claim.claim_id}
        </Link>

        {claim.verdict ? <VerdictBadge verdict={claim.verdict} /> : null}
      </CardHeader>

      <CardContent className="space-y-3">
        <p className="leading-relaxed">{claim.claim_text}</p>

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

          {claim.support_count ? (
            <span className="rounded bg-emerald-100 px-2 py-0.5 text-emerald-800">
              {claim.support_count} supporting
            </span>
          ) : null}

          {claim.contradiction_count ? (
            <span className="rounded bg-red-100 px-2 py-0.5 text-red-800">
              {claim.contradiction_count} contradicting
            </span>
          ) : null}
        </div>

        {claim.source_sentence ? (
          <div>
            <p className="mb-1 text-xs font-semibold uppercase text-muted-foreground">
              Source sentence
            </p>

            <blockquote className="border-l-4 border-amber-400 bg-amber-50 p-3 text-sm leading-relaxed dark:bg-amber-500/10">
              {claim.source_sentence}
            </blockquote>

            <div className="mt-1 flex items-center gap-3">
              {claim.start_offset != null && claim.end_offset != null ? (
                <span className="font-mono text-xs text-muted-foreground">
                  offset {claim.start_offset}–{claim.end_offset}
                </span>
              ) : null}

              <Link
                to={`/papers/${claim.paper_id}/view?claim=${claim.claim_id}`}
                className="text-xs font-semibold text-primary hover:underline"
              >
                View in paper →
              </Link>
            </div>
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

        <EvidenceList
          items={claim.supporting_evidence ?? []}
          kind="supporting"
        />

        <EvidenceList
          items={claim.contradicting_evidence ?? []}
          kind="contradicting"
        />

        {claim.flags?.length ? (
          <div className="space-y-2">
            {claim.flags.map((flag, index) => (
              <FlagCard key={index} flag={flag} />
            ))}
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}
