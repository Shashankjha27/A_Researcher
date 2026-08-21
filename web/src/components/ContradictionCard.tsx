import { Link } from "react-router"

import { AlertTriangle } from "lucide-react"

import type { ContradictionItem } from "@/api/types"
import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { DiffText } from "@/components/WordDiff"

function Side({
  label,
  side,
  otherText,
  diffSide,
  ownText,
}: {
  label: string
  side: ContradictionItem["claim_a"]
  otherText: string
  diffSide: "a" | "b"
  ownText: string
}) {
  if (!side) {
    return (
      <div className="rounded-lg bg-muted p-4 text-sm text-muted-foreground">
        {label}: data unavailable.
      </div>
    )
  }

  return (
    <div className="min-w-0 rounded-lg bg-muted p-4">
      <p className="mb-2 text-xs font-bold uppercase text-muted-foreground">
        {label}
      </p>

      <DiffText
        textA={ownText}
        textB={otherText}
        side={diffSide}
        className="font-semibold leading-relaxed"
      />

      {side.source_sentence ? (
        <blockquote className="mt-3 border-l-4 border-amber-400 bg-amber-50 p-3 text-sm leading-relaxed">
          <DiffText
            textA={ownText}
            textB={otherText}
            side={diffSide}
            className="inline"
          />
        </blockquote>
      ) : null}

      <Link
        to={`/reports/${side.paper_id}/claims/${side.claim_id}`}
        className="mt-2 inline-block text-xs font-semibold text-primary hover:underline"
      >
        View claim →
      </Link>
    </div>
  )
}

export function ContradictionCard({
  item,
  index,
}: {
  item: ContradictionItem
  index: number
}) {
  const textA = item.claim_a?.source_sentence ?? item.claim_a?.claim_text ?? ""
  const textB = item.claim_b?.source_sentence ?? item.claim_b?.claim_text ?? ""

  return (
    <Card className="border-red-200">
      <CardHeader className="flex-row items-center justify-between space-y-0 bg-red-50 py-3">
        <CardTitle className="flex items-center gap-2 text-sm font-bold text-red-800">
          <AlertTriangle className="size-4" />
          Contradiction pair {index + 1}
        </CardTitle>

        <Badge variant="outline" className="border-red-300 text-red-800">
          NLI {item.nli_probability.toFixed(3)}
        </Badge>
      </CardHeader>

      <CardContent className="grid gap-4 pt-4 md:grid-cols-[1fr_auto_1fr]">
        <Side
          label="Claim A"
          side={item.claim_a}
          ownText={textA}
          otherText={textB}
          diffSide="a"
        />

        <div className="flex items-center justify-center font-extrabold text-red-800">
          VS
        </div>

        <Side
          label="Claim B"
          side={item.claim_b}
          ownText={textB}
          otherText={textA}
          diffSide="b"
        />
      </CardContent>

      <p className="px-6 pb-4 text-xs text-muted-foreground">
        <span className="mr-3 inline-flex items-center gap-1">
          <span className="inline-block size-2.5 rounded-sm bg-red-200 dark:bg-red-500/40" />
          unique to Claim A
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="inline-block size-2.5 rounded-sm bg-emerald-200 dark:bg-emerald-500/40" />
          unique to Claim B
        </span>
      </p>
    </Card>
  )
}
