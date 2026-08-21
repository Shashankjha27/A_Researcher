import { useEffect, useRef, useState } from "react"

import type { ClaimRecord } from "@/api/types"

const COMPONENT_LABELS: Record<string, string> = {
  nli_confidence: "NLI",
  evidence_strength: "Evidence",
  agreement: "Agreement",
}

function useCountUp(target: number, durationMs = 700): number {
  const [value, setValue] = useState(0)
  const frame = useRef<number | null>(null)

  useEffect(() => {
    const start = performance.now()
    const from = 0

    const tick = (now: number) => {
      const progress = Math.min(1, (now - start) / durationMs)
      const eased = 1 - (1 - progress) ** 3

      setValue(from + (target - from) * eased)

      if (progress < 1) {
        frame.current = requestAnimationFrame(tick)
      }
    }

    frame.current = requestAnimationFrame(tick)

    return () => {
      if (frame.current !== null) {
        cancelAnimationFrame(frame.current)
      }
    }
  }, [target, durationMs])

  return value
}

function AnimatedBar({ label, value }: { label: string; value: number }) {
  const clamped = Math.max(0, Math.min(1, value))
  const animated = useCountUp(clamped)

  return (
    <div className="flex items-center gap-3">
      <span className="w-20 shrink-0 text-xs text-muted-foreground">
        {label}
      </span>

      <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-primary transition-[width] duration-700 ease-out"
          style={{ width: `${animated * 100}%` }}
        />
      </div>

      <span className="w-12 shrink-0 text-right font-mono text-xs tabular-nums">
        {animated.toFixed(3)}
      </span>
    </div>
  )
}

export function ConfidenceBars({
  components,
}: {
  components: ClaimRecord["confidence_components"]
}) {
  if (!components || Object.keys(components).length === 0) {
    return null
  }

  return (
    <div className="mt-3 space-y-2">
      <p className="text-xs font-semibold uppercase text-muted-foreground">
        Confidence components
      </p>

      {Object.entries(components).map(([key, value]) => (
        <AnimatedBar
          key={key}
          label={COMPONENT_LABELS[key] ?? key}
          value={value}
        />
      ))}
    </div>
  )
}
