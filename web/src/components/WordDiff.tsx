import { diffWords } from "diff"

import { cn } from "@/lib/utils"

export type DiffSide = "a" | "b"

interface DiffPart {
  value: string
  uniqueToSide: boolean
  render: boolean
}

/**
 * Word-level diff of two claim texts.
 *
 * Side "a" renders the parts that make up textA (highlighting words
 * missing from textB); side "b" mirrors it. Shared words stay neutral,
 * so the conflicting wording pops out without reading.
 */
export function buildDiffParts(
  textA: string,
  textB: string,
  side: DiffSide,
): DiffPart[] {
  return diffWords(textA, textB).map((part) => {
    if (side === "a") {
      return {
        value: part.value,
        uniqueToSide: Boolean(part.removed),
        render: !part.added,
      }
    }

    return {
      value: part.value,
      uniqueToSide: Boolean(part.added),
      render: !part.removed,
    }
  })
}

export function DiffText({
  textA,
  textB,
  side,
  className,
}: {
  textA: string
  textB: string
  side: DiffSide
  className?: string
}) {
  const parts = buildDiffParts(textA, textB, side)

  return (
    <p className={className}>
      {parts
        .filter((part) => part.render)
        .map((part, index) =>
          part.uniqueToSide ? (
            <mark
              key={index}
              className={cn(
                "rounded px-0.5",
                side === "a"
                  ? "bg-red-200/70 text-red-900 dark:bg-red-500/25 dark:text-red-100"
                  : "bg-emerald-200/70 text-emerald-900 dark:bg-emerald-500/25 dark:text-emerald-100",
              )}
            >
              {part.value}
            </mark>
          ) : (
            <span key={index}>{part.value}</span>
          ),
        )}
    </p>
  )
}
