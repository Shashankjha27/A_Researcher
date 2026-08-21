import { Link } from "react-router"

import type { BenchmarkResult } from "@/api/types"
import { Badge } from "@/components/ui/badge"
import { ShieldCheck } from "lucide-react"

const BENCHMARK_STORAGE_KEY = "ar.benchmark.last"

function readLastBenchmark(): BenchmarkResult | null {
  try {
    const raw = localStorage.getItem(BENCHMARK_STORAGE_KEY)

    return raw ? (JSON.parse(raw) as BenchmarkResult) : null
  } catch {
    return null
  }
}

export function TrustLedger({ nliModel }: { nliModel?: string }) {
  const benchmark = readLastBenchmark()

  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-lg border bg-muted/30 px-4 py-2.5 text-xs">
      <span className="flex items-center gap-1.5 font-semibold">
        <ShieldCheck className="size-4 text-primary" aria-hidden />
        Trust ledger
      </span>

      {nliModel ? (
        <span className="font-mono text-muted-foreground">{nliModel}</span>
      ) : (
        <span className="text-muted-foreground">NLI model unknown</span>
      )}

      <span className="text-border">|</span>

      {benchmark ? (
        <>
          <span className="text-muted-foreground">
            SciFact macro F1{" "}
            <span className="font-mono font-semibold text-foreground">
              {benchmark.macro.f1.toFixed(2)}
            </span>{" "}
            @ threshold{" "}
            <span className="font-mono font-semibold text-foreground">
              {benchmark.threshold.toFixed(2)}
            </span>{" "}
            ({benchmark.split})
          </span>

          <Badge
            variant="outline"
            className="border-emerald-500/40 text-[10px] uppercase text-emerald-600 dark:text-emerald-400"
          >
            NLI core — not an LLM prompt
          </Badge>
        </>
      ) : (
        <Link
          to="/benchmark"
          className="font-semibold text-primary hover:underline"
        >
          No benchmark run yet — run it →
        </Link>
      )}
    </div>
  )
}
