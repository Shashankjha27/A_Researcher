import { useEffect, useState } from "react"
import { toast } from "sonner"

import {
  benchmarkResultFromJob,
  useJob,
  useSubmitBenchmarkJob,
} from "@/api/hooks"
import type { BenchmarkResult } from "@/api/types"
import { JobProgress } from "@/components/JobProgress"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Slider } from "@/components/ui/slider"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

const STORAGE_KEY = "ar.benchmark.last"

function MetricsTable({ result }: { result: BenchmarkResult }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">
          SciFact results — split “{result.split}”, threshold{" "}
          {result.threshold.toFixed(2)}, {result.claims_count} claims
        </CardTitle>

        {result.nli_model ? (
          <CardDescription className="font-mono text-xs">
            checkpoint: {result.nli_model}
          </CardDescription>
        ) : null}
      </CardHeader>

      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Label</TableHead>

              <TableHead className="text-right">Precision</TableHead>

              <TableHead className="text-right">Recall</TableHead>

              <TableHead className="text-right">F1</TableHead>
            </TableRow>
          </TableHeader>

          <TableBody>
            {result.labels.map((row) => (
              <TableRow key={row.label}>
                <TableCell className="font-medium">{row.label}</TableCell>

                <TableCell className="text-right font-mono text-xs">
                  {row.precision.toFixed(4)}
                </TableCell>

                <TableCell className="text-right font-mono text-xs">
                  {row.recall.toFixed(4)}
                </TableCell>

                <TableCell className="text-right font-mono text-xs">
                  {row.f1.toFixed(4)}
                </TableCell>
              </TableRow>
            ))}

            <TableRow className="bg-muted/50 font-bold">
              <TableCell>MACRO</TableCell>

              <TableCell className="text-right font-mono text-xs">
                {result.macro.precision.toFixed(4)}
              </TableCell>

              <TableCell className="text-right font-mono text-xs">
                {result.macro.recall.toFixed(4)}
              </TableCell>

              <TableCell className="text-right font-mono text-xs">
                {result.macro.f1.toFixed(4)}
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}

export function BenchmarkPage() {
  const [split, setSplit] = useState("dev")
  const [threshold, setThreshold] = useState(0.7)
  const [jobId, setJobId] = useState<string | null>(null)
  const [lastResult, setLastResult] = useState<BenchmarkResult | null>(
    () => {
      try {
        const raw = localStorage.getItem(STORAGE_KEY)

        return raw ? (JSON.parse(raw) as BenchmarkResult) : null
      } catch {
        return null
      }
    },
  )

  const submitJob = useSubmitBenchmarkJob()
  const { data: job } = useJob(jobId)
  const finished = benchmarkResultFromJob(job)

  useEffect(() => {
    if (!finished) {
      return
    }

    setLastResult(finished)

    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(finished))
    } catch {
      // storage unavailable — ignore
    }
  }, [finished])

  function handleRun() {
    submitJob.mutate(
      { split, threshold },
      {
        onSuccess: (response) => setJobId(response.job_id),
        onError: (error) => {
          toast.error(
            error instanceof Error ? error.message : "Failed to start.",
          )
        },
      },
    )
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <h1 className="text-2xl font-bold">SciFact benchmark</h1>

      <Card>
        <CardHeader>
          <CardTitle>Run benchmark</CardTitle>

          <CardDescription>
            Runs the NLI + retrieval stages over a SciFact slice and reports
            precision / recall / F1. This is the number that goes on the
            slide.
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-5">
          <div className="grid gap-4 sm:grid-cols-[200px_1fr]">
            <div className="space-y-1.5">
              <Label>Split</Label>

              <Select value={split} onValueChange={setSplit}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>

                <SelectContent>
                  <SelectItem value="train">train</SelectItem>

                  <SelectItem value="dev">dev</SelectItem>

                  <SelectItem value="test">test</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>NLI threshold</Label>

                <span className="font-mono text-sm">
                  {threshold.toFixed(2)}
                </span>
              </div>

              <Slider
                min={0.5}
                max={0.95}
                step={0.01}
                value={[threshold]}
                onValueChange={(values) => setThreshold(values[0] ?? 0.7)}
              />
            </div>
          </div>

          <Button onClick={handleRun} disabled={submitJob.isPending}>
            Run benchmark
          </Button>
        </CardContent>
      </Card>

      {jobId ? <JobProgress job={job} /> : null}

      {lastResult ? <MetricsTable result={lastResult} /> : null}
    </div>
  )
}
