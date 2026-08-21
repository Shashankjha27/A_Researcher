import { useState } from "react"
import { Link } from "react-router"

import { api } from "@/api/client"
import { useConfig, useHealth, useJob, usePapers } from "@/api/hooks"
import type { BenchmarkResult } from "@/api/types"
import { JobProgress } from "@/components/JobProgress"
import { Logo } from "@/components/Logo"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  ArrowRight,
  FileText,
  FlaskConical,
  Flag,
  Gauge,
  Library as LibraryIcon,
  Play,
  Scale,
  ScanSearch,
  ScrollText,
  Settings as SettingsIcon,
  Sparkles,
} from "lucide-react"
import { cn } from "@/lib/utils"

const BENCHMARK_STORAGE_KEY = "ar.benchmark.last"

function useLastBenchmark(): BenchmarkResult | null {
  try {
    const raw = localStorage.getItem(BENCHMARK_STORAGE_KEY)

    return raw ? (JSON.parse(raw) as BenchmarkResult) : null
  } catch {
    return null
  }
}

function HealthBadge() {
  const { data, isError } = useHealth()

  const ok = !isError && data?.status === "ok"

  return (
    <Badge
      variant="outline"
      className={cn(
        "gap-1.5",
        ok
          ? "border-emerald-500/40 text-emerald-600 dark:text-emerald-400"
          : "border-red-500/40 text-red-600 dark:text-red-400",
      )}
    >
      <span
        className={cn(
          "inline-block size-2 rounded-full",
          ok ? "bg-emerald-500" : "bg-red-500",
        )}
      />
      {ok ? "API online" : "API offline"}
    </Badge>
  )
}

interface TileProps {
  to: string
  icon: React.ReactNode
  title: string
  description: string
  meta?: React.ReactNode
}

function Tile({ to, icon, title, description, meta }: TileProps) {
  return (
    <Link to={to} className="group focus-visible:outline-none">
      <Card className="h-full transition-all group-hover:-translate-y-0.5 group-hover:border-primary/50 group-hover:shadow-md group-focus-visible:ring-3 group-focus-visible:ring-ring/50">
        <CardHeader className="gap-2 p-4">
          <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
            {icon}
          </div>

          <div className="space-y-1">
            <CardTitle className="flex items-center justify-between text-base">
              {title}

              <span
                aria-hidden
                className="text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100"
              >
                →
              </span>
            </CardTitle>

            <CardDescription className="text-xs">
              {description}
            </CardDescription>
          </div>

          {meta ? (
            <div className="font-mono text-xs text-muted-foreground">
              {meta}
            </div>
          ) : null}
        </CardHeader>
      </Card>
    </Link>
  )
}

const PIPELINE = [
  {
    icon: <FileText className="size-4" aria-hidden />,
    title: "Extract",
    text: "Pull empirical claims out of each paper as structured data.",
    detail:
      "LLM output passes a JSON-schema gate with ≤ 2 retries — malformed extractions never reach the store.",
  },
  {
    icon: <ScanSearch className="size-4" aria-hidden />,
    title: "Verify",
    text: "Cross-check every claim pair: entailment / contradiction / neutral.",
    detail:
      "Pretrained NLI classifier (DeBERTa-v3 / SciFact-tuned); precision / recall / F1 measured on SciFact.",
  },
  {
    icon: <Flag className="size-4" aria-hidden />,
    title: "Flag",
    text: "Rule-based integrity checks on every claim.",
    detail:
      "Small samples, single-study consensus, funding conflicts, citation laundering, retracted references.",
  },
  {
    icon: <Gauge className="size-4" aria-hidden />,
    title: "Score",
    text: "A transparent confidence score per claim.",
    detail:
      "Deterministic pure functions over evidence counts and flag severities — no LLM guessing.",
  },
  {
    icon: <ScrollText className="size-4" aria-hidden />,
    title: "Synthesize",
    text: "A structured report grouped by subtopic.",
    detail:
      "Support, dissent, flags, verdict — every claim linked back to its exact source sentence.",
  },
]

const NLI_VS_LLM = [
  {
    aspect: "Role",
    nli: "The judge — cross-examines claims",
    llm: "The reader — extracts and argues",
  },
  {
    aspect: "Tasks",
    nli: "Scores every claim pair: entailment / contradiction / neutral, with probabilities",
    llm: "Extracts empirical claims into a strict JSON schema; plays defender / attacker / judge in debate mode; fills missing metadata",
  },
  {
    aspect: "Determinism",
    nli: "Pure classifier — same input, same verdict",
    llm: "Generative — output varies run to run",
  },
  {
    aspect: "Benchmarked",
    nli: "Yes — SciFact precision / recall / F1 on the Benchmark page",
    llm: "No — quality is contained, not measured",
  },
  {
    aspect: "Trust boundary",
    nli: "Sole source of support / contradiction signals",
    llm: "Never trusted alone — schema-gated and anchored to exact source offsets",
  },
]

const ARCHITECTURE_FLOW = [
  "Papers (PDF / txt / md)",
  "Ingest & chunk",
  "Claim extraction",
  "NLI engine",
  "Integrity flags",
  "Confidence score",
  "Report",
]

const TECH_STACK = [
  {
    layer: "Backend",
    choice: "FastAPI + Pydantic v2",
    why: "Interactive API docs; schema gate for LLM output",
  },
  {
    layer: "Contradiction detection",
    choice: "Pretrained NLI (DeBERTa-v3 / SciFact-tuned)",
    why: "Deterministic, benchmarkable, ~500 MB",
  },
  {
    layer: "Pair reduction",
    choice: "MiniLM embeddings + clustering",
    why: "O(n²) claim pairs → tractable",
  },
  {
    layer: "Claim extraction",
    choice: "Any LLM (API or local)",
    why: "Judgement task; shape guaranteed by schema gate",
  },
  {
    layer: "Scoring & flags",
    choice: "Pure Python functions",
    why: "Explainable, zero LLM guessing",
  },
  {
    layer: "Storage",
    choice: "JSONL document store",
    why: "Prototype scope — no queues, no vector DB",
  },
]

function DemoStrip() {
  const [jobId, setJobId] = useState<string | null>(null)
  const [starting, setStarting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const { data: job } = useJob(jobId)

  const runLive = async () => {
    setStarting(true)
    setError(null)

    try {
      const body = await api.post<{ job_id: string }>("/demo/run-live")

      setJobId(body.job_id)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start job")
    } finally {
      setStarting(false)
    }
  }

  return (
    <div className="space-y-2 rounded-xl border bg-primary/5 p-4">
      <p className="flex items-center gap-1.5 text-sm font-semibold">
        <Sparkles className="size-4 text-primary" aria-hidden />
        See it in action
      </p>

      <p className="text-sm leading-relaxed text-muted-foreground">
        Open a pre-verified demo report instantly, or re-run the full
        pipeline on the same paper live.
      </p>

      <div className="flex flex-wrap items-center gap-2 pt-1">
        <Button asChild size="sm">
          <Link to="/reports/paper-demo-golden">
            <FileText className="size-4" aria-hidden />
            View demo report
          </Link>
        </Button>

        <Button
          variant="outline"
          size="sm"
          onClick={runLive}
          disabled={starting || job?.status === "running" || job?.status === "queued"}
        >
          <Play className="size-4" aria-hidden />
          {starting ? "Starting…" : "Run live verification"}
        </Button>
      </div>

      {error ? (
        <p className="text-xs text-red-600 dark:text-red-400">{error}</p>
      ) : null}

      {jobId ? (
        <div className="pt-1">
          <JobProgress job={job} />
        </div>
      ) : null}
    </div>
  )
}

export function HomePage() {
  const { data: papers } = usePapers()
  const { data: config } = useConfig()
  const benchmark = useLastBenchmark()

  const paperCount = papers?.length ?? 0

  return (
    <div className="space-y-12">
      <div className="grid gap-x-10 gap-y-8 lg:min-h-[calc(100svh-3rem)] lg:grid-cols-2">
        <header className="space-y-4 lg:pt-6">
          <div className="flex items-center gap-3">
            <Logo className="size-11 rounded-2xl" />

            <div className="flex min-w-0 flex-col">
              <h1 className="text-3xl leading-none font-bold tracking-tight">
                A_Researcher
              </h1>

              <span className="mt-0.5 text-[11px] tracking-wide text-muted-foreground">
                artificial Researcher
              </span>
            </div>

            <HealthBadge />
          </div>

          <p className="max-w-xl leading-relaxed text-muted-foreground">
            Cross-examining research papers: claims are extracted with an LLM,
            checked against the paper's own evidence and its cited references
            with an NLI engine, and flagged as supported, contradicted, or
            insufficient.
          </p>

          <p className="max-w-xl text-sm leading-relaxed text-muted-foreground">
            Not summarizing — cross-examining. A paper is treated like a
            witness: what it actually claims is extracted first, then each
            claim is cross-examined against evidence before it gets a verdict.
          </p>

          <DemoStrip />
        </header>

        <div className="grid content-center gap-4 sm:grid-cols-2">
          <Tile
            to="/verify"
            icon={<ScanSearch className="size-5" />}
            title="Verify papers"
            description="Upload PDFs or paste an arXiv link — claims are extracted and cross-checked."
          />

          <Tile
            to="/benchmark"
            icon={<FlaskConical className="size-5" />}
            title="Benchmark"
            description="SciFact precision / recall / F1 for the NLI core."
            meta={
              benchmark
                ? `macro F1 ${benchmark.macro.f1.toFixed(2)} · ${benchmark.split} @ ${benchmark.threshold.toFixed(2)}`
                : "no runs yet"
            }
          />

          <Tile
            to="/library"
            icon={<LibraryIcon className="size-5" />}
            title="Library"
            description="Every ingested paper and its verification report."
            meta={`${paperCount} paper${paperCount === 1 ? "" : "s"}`}
          />

          <Tile
            to="/settings"
            icon={<SettingsIcon className="size-5" />}
            title="Settings"
            description="LLM provider, model, API key, and appearance."
            meta={
              config?.provider
                ? `${config.provider}${config.model ? ` · ${config.model}` : ""}`
                : "not configured"
            }
          />
        </div>

        <section className="space-y-3 self-start">
          <h2 className="text-xl font-bold tracking-tight">
            What the NLI does vs what the LLM does
          </h2>

          <Card className="bg-muted/30 py-2 [&_[data-slot=table-container]]:overflow-x-hidden">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-24" />

                  <TableHead>
                    <span className="flex items-center gap-1.5">
                      <ScanSearch
                        className="size-4 text-primary"
                        aria-hidden
                      />
                      NLI engine
                    </span>
                  </TableHead>

                  <TableHead>
                    <span className="flex items-center gap-1.5">
                      <FileText className="size-4 text-primary" aria-hidden />
                      LLM
                    </span>
                  </TableHead>
                </TableRow>
              </TableHeader>

              <TableBody>
                {NLI_VS_LLM.map((row) => (
                  <TableRow key={row.aspect}>
                    <TableCell className="w-24 align-top font-medium whitespace-normal">
                      {row.aspect}
                    </TableCell>

                    <TableCell className="px-3 py-4 align-top leading-relaxed whitespace-normal text-muted-foreground">
                      {row.nli}
                    </TableCell>

                    <TableCell className="px-3 py-4 align-top leading-relaxed whitespace-normal text-muted-foreground">
                      {row.llm}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>

          <aside className="rounded-lg border-l-4 border-primary bg-primary/5 p-4">
            <div className="flex items-start gap-3">
              <Scale
                className="mt-0.5 size-5 shrink-0 text-primary"
                aria-hidden
              />

              <div className="space-y-1">
                <p className="text-sm font-semibold">
                  The key design decision
                </p>

                <p className="text-sm leading-relaxed text-muted-foreground">
                  Contradiction detection is an NLI classifier — never an LLM
                  prompt. That is what makes the core deterministic and
                  benchmarkable against SciFact, and it's the whole reason this
                  isn't just another summarizer wrapper.
                </p>
              </div>
            </div>
          </aside>
        </section>

        <section className="space-y-4 self-start">
          <h2 className="text-xl font-bold tracking-tight">
            How a paper gets cross-examined
          </h2>

          <ol className="space-y-3">
            {PIPELINE.map((step, index) => (
              <li
                key={step.title}
                className="rounded-xl border bg-foreground/[0.03] p-4"
              >
                <div className="flex items-start gap-3">
                  <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
                    {step.icon}
                  </span>

                  <div className="space-y-1">
                    <p className="font-semibold">
                      <span className="mr-1.5 font-mono text-xs text-muted-foreground">
                        {String(index + 1).padStart(2, "0")}
                      </span>
                      {step.title}
                    </p>

                    <p className="text-sm leading-relaxed">{step.text}</p>

                    <p className="text-sm leading-relaxed text-muted-foreground">
                      {step.detail}
                    </p>
                  </div>
                </div>
              </li>
            ))}
          </ol>
        </section>
      </div>

      <section className="space-y-3 rounded-xl bg-foreground/[0.02] p-4">
        <h2 className="text-xl font-bold tracking-tight">Architecture</h2>

        <p className="text-sm text-muted-foreground">
          One monolithic FastAPI service over a JSONL document store. No
          queues, no vector database, no training — inference only.
        </p>

        <div className="flex flex-wrap items-center gap-2">
          {ARCHITECTURE_FLOW.map((stage, index) => (
            <span key={stage} className="flex items-center gap-2">
              <span className="rounded-md border bg-muted/50 px-2.5 py-1 font-mono text-xs">
                {stage}
              </span>

              {index < ARCHITECTURE_FLOW.length - 1 ? (
                <ArrowRight
                  className="size-3.5 shrink-0 text-muted-foreground"
                  aria-hidden
                />
              ) : null}
            </span>
          ))}
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-bold tracking-tight">Tech stack</h2>

        <Card className="bg-muted/30 py-2">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-44">Layer</TableHead>

                <TableHead>Choice</TableHead>

                <TableHead className="hidden sm:table-cell">Why</TableHead>
              </TableRow>
            </TableHeader>

            <TableBody>
              {TECH_STACK.map((row) => (
                <TableRow key={row.layer}>
                  <TableCell className="font-medium">{row.layer}</TableCell>

                  <TableCell>{row.choice}</TableCell>

                  <TableCell className="hidden text-muted-foreground sm:table-cell">
                    {row.why}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      </section>

      <footer className="rounded-lg bg-foreground/[0.02] p-4">
        <p className="text-xs leading-relaxed text-muted-foreground">
          AI transparency: this project is human-built; AI was used strictly
          as an assistance tool. Every block of code and concept is
          human-reviewed — the AI never takes responsibility for the work.
        </p>
      </footer>
    </div>
  )
}
