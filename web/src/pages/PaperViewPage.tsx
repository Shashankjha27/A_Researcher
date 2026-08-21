import { useEffect, useRef } from "react"
import { Link, useParams, useSearchParams } from "react-router"

import { useClaim, usePaperBlocks } from "@/api/hooks"
import type { PaperBlock } from "@/api/types"
import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

function BlockParagraph({
  block,
  start,
  end,
  markRef,
}: {
  block: PaperBlock
  start: number | null
  end: number | null
  markRef?: React.RefObject<HTMLElement | null>
}) {
  const hasSpan =
    start != null &&
    end != null &&
    end > block.start_offset &&
    start < block.end_offset

  if (!hasSpan) {
    return <p className="text-sm leading-relaxed">{block.text}</p>
  }

  const sliceStart = Math.max(start!, block.start_offset) - block.start_offset
  const sliceEnd = Math.min(end!, block.end_offset) - block.start_offset

  return (
    <p className="text-sm leading-relaxed">
      {block.text.slice(0, sliceStart)}

      <mark
        ref={markRef}
        className="rounded bg-amber-300/60 px-0.5 text-inherit ring-2 ring-amber-400/60 dark:bg-amber-500/30 dark:text-foreground"
      >
        {block.text.slice(sliceStart, sliceEnd)}
      </mark>

      {block.text.slice(sliceEnd)}
    </p>
  )
}

export function PaperViewPage() {
  const { paperId = "" } = useParams()
  const [searchParams] = useSearchParams()
  const claimId = searchParams.get("claim")

  const { data: paper, isLoading, isError } = usePaperBlocks(paperId)
  const { data: claimData } = useClaim(claimId ?? "")

  const markRef = useRef<HTMLElement | null>(null)

  const claim = claimData?.claim as
    | { start_offset?: number; end_offset?: number; claim_text?: string }
    | undefined

  useEffect(() => {
    if (!paper || !markRef.current) {
      return
    }

    markRef.current.scrollIntoView({
      behavior: "smooth",
      block: "center",
    })
  }, [paper])

  if (isLoading) {
    return (
      <div className="mx-auto max-w-4xl space-y-3">
        <Skeleton className="h-8 w-2/3" />

        <Skeleton className="h-4 w-40" />

        <div className="space-y-2 pt-4">
          {[0, 1, 2, 3, 4, 5, 6].map((row) => (
            <Skeleton key={row} className="h-5 w-full" />
          ))}

          <Skeleton className="h-5 w-3/4" />
        </div>
      </div>
    )
  }

  if (isError || !paper) {
    return (
      <p className="text-sm text-red-600">
        Failed to load paper view.
      </p>
    )
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex items-start justify-between gap-4 pt-4">
        <div>
          <h1 className="text-xl font-bold leading-snug">
            {paper.title}
          </h1>

          <p className="mt-1 font-mono text-xs text-muted-foreground">
            {paper.paper_id}
          </p>
        </div>

        <Link
          to={`/reports/${paperId}`}
          className="shrink-0 text-sm text-muted-foreground hover:text-foreground"
        >
          ← Report
        </Link>
      </div>

      {claim?.claim_text ? (
        <Card className="border-amber-400/50">
          <CardHeader className="py-4">
            <div className="flex items-center justify-between gap-2">
              <Badge variant="outline">Viewing claim</Badge>

              {claimId ? (
                <Link
                  to={`/reports/${paperId}/claims/${claimId}`}
                  className="text-xs font-semibold text-primary hover:underline"
                >
                  Open claim detail →
                </Link>
              ) : null}
            </div>

            <CardTitle className="text-sm font-medium leading-relaxed">
              {claim.claim_text}
            </CardTitle>
          </CardHeader>
        </Card>
      ) : null}

      <div className="space-y-6">
        {paper.blocks.map((block, index) => (
          <section key={index} className="space-y-2">
            <h2 className="font-mono text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              {block.section}
            </h2>

            <BlockParagraph
              block={block}
              start={claim?.start_offset ?? null}
              end={claim?.end_offset ?? null}
              markRef={
                claim &&
                claim.start_offset != null &&
                claim.end_offset != null &&
                block.start_offset <= claim.start_offset &&
                claim.start_offset < block.end_offset
                  ? markRef
                  : undefined
              }
            />
          </section>
        ))}
      </div>
    </div>
  )
}
