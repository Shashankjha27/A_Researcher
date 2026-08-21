import { useEffect, useRef } from "react"
import { Link } from "react-router"

import { toast } from "sonner"

import type { JobRecord, VerifyJobResult } from "@/api/types"
import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

const STAGE_LABELS: Record<string, string> = {
  ingest: "Ingesting",
  extract: "Extracting claims",
  evidence: "Retrieving evidence",
  nli: "Running NLI",
  score: "Scoring",
}

const STATUS_STYLES: Record<string, string> = {
  queued: "bg-yellow-100 text-yellow-800",
  running: "bg-blue-100 text-blue-800",
  done: "bg-emerald-100 text-emerald-800",
  error: "bg-red-100 text-red-800",
}

export function JobProgress({ job }: { job: JobRecord | undefined }) {
  const lastStatus = useRef<string | null>(null)

  useEffect(() => {
    if (!job) {
      return
    }

    const previous = lastStatus.current
    lastStatus.current = job.status

    if (previous === null || previous === job.status) {
      return
    }

    if (job.status === "done") {
      toast.success(
        job.kind === "benchmark"
          ? "Benchmark finished."
          : "Verification finished.",
      )
    } else if (job.status === "error") {
      toast.error(job.error ?? "Job failed.")
    }
  }, [job])

  if (!job) {
    return (
      <Card>
        <CardContent className="space-y-2 pt-6">
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-2 w-full" />
        </CardContent>
      </Card>
    )
  }

  const percent =
    job.progress.total > 0
      ? (job.progress.done / job.progress.total) * 100
      : 0

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle className="text-sm">Job {job.job_id}</CardTitle>

        <Badge
          className={`border-transparent uppercase ${STATUS_STYLES[job.status] ?? ""}`}
        >
          {job.status}
        </Badge>
      </CardHeader>

      <CardContent className="space-y-3">
        <div className="h-2 overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-primary transition-all"
            style={{ width: `${percent}%` }}
          />
        </div>

        <p className="text-xs text-muted-foreground">
          {job.progress.done}/{job.progress.total} papers
          {job.progress.stage
            ? ` — ${STAGE_LABELS[job.progress.stage] ?? job.progress.stage}`
            : ""}
        </p>

        {job.status === "error" ? (
          <p className="rounded-md bg-red-50 p-3 text-sm text-red-800">
            {job.error ?? "Unknown error"}
          </p>
        ) : null}

        {job.status === "done" && job.kind === "verify"
          ? (job.results as VerifyJobResult[] | null)?.map((result) => (
              <Link
                key={result.paper.paper_id}
                to={`/reports/${result.paper.paper_id}`}
                className="block rounded-md bg-muted px-3 py-2 text-sm font-medium hover:bg-accent"
              >
                View report: {result.paper.title ?? result.paper.paper_id} →
              </Link>
            ))
          : null}
      </CardContent>
    </Card>
  )
}
