import { useState } from "react"
import { toast } from "sonner"

import {
  fetchPapers,
  useIngestPaper,
  useIngestUrl,
  useJob,
  useSubmitVerifyJob,
} from "@/api/hooks"
import type { VerifyPaperInput } from "@/api/types"
import { JobProgress } from "@/components/JobProgress"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Slider } from "@/components/ui/slider"
import { X } from "lucide-react"

interface QueueItem {
  id: string
  label: string
  file?: File
  ingested?: { paperId: string }
}

type SourceMode = "upload" | "arxiv"

const PROVIDERS = [
  { value: "ollama", label: "Ollama" },
  { value: "openai", label: "OpenAI" },
  { value: "gemini", label: "Gemini" },
  { value: "claude", label: "Claude" },
]

function OptionsPanel({
  evidenceTopK,
  setEvidenceTopK,
  pairThreshold,
  setPairThreshold,
  nliEnabled,
  setNliEnabled,
  nliThreshold,
  setNliThreshold,
  provider,
  setProvider,
  model,
  setModel,
}: {
  evidenceTopK: number
  setEvidenceTopK: (value: number) => void
  pairThreshold: number
  setPairThreshold: (value: number) => void
  nliEnabled: boolean
  setNliEnabled: (value: boolean) => void
  nliThreshold: number
  setNliThreshold: (value: number) => void
  provider: string
  setProvider: (value: string) => void
  model: string
  setModel: (value: string) => void
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Options</CardTitle>

        <CardDescription>
          Thresholds trade precision against recall. Defaults match the
          backend config.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-5">
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label>Evidence top-k</Label>

            <span className="font-mono text-sm">{evidenceTopK}</span>
          </div>

          <Slider
            min={1}
            max={10}
            step={1}
            value={[evidenceTopK]}
            onValueChange={(values) => setEvidenceTopK(values[0] ?? 5)}
          />
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label>Pair similarity threshold</Label>

            <span className="font-mono text-sm">
              {pairThreshold.toFixed(2)}
            </span>
          </div>

          <Slider
            min={0}
            max={1}
            step={0.05}
            value={[pairThreshold]}
            onValueChange={(values) => setPairThreshold(values[0] ?? 0.75)}
          />
        </div>

        <div className="space-y-2">
          <label className="flex items-center gap-2 text-sm font-medium">
            <input
              type="checkbox"
              checked={nliEnabled}
              onChange={(event) => setNliEnabled(event.target.checked)}
              className="size-4"
            />
            Override NLI contradiction threshold
          </label>

          {nliEnabled ? (
            <>
              <div className="flex items-center justify-between">
                <Label>NLI threshold</Label>

                <span className="font-mono text-sm">
                  {nliThreshold.toFixed(2)}
                </span>
              </div>

              <Slider
                min={0.5}
                max={0.95}
                step={0.01}
                value={[nliThreshold]}
                onValueChange={(values) => setNliThreshold(values[0] ?? 0.85)}
              />
            </>
          ) : null}
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label>LLM provider override</Label>

            <Select value={provider} onValueChange={setProvider}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Server default" />
              </SelectTrigger>

              <SelectContent>
                {PROVIDERS.map((providerItem) => (
                  <SelectItem
                    key={providerItem.value}
                    value={providerItem.value}
                  >
                    {providerItem.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label>Model override</Label>

            <Input
              value={model}
              onChange={(event) => setModel(event.target.value)}
              placeholder="Server default"
            />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export function VerifyPage() {
  const [queue, setQueue] = useState<QueueItem[]>([])
  const [sourceMode, setSourceMode] = useState<SourceMode>("upload")
  const [arxivUrl, setArxivUrl] = useState("")
  const [jobId, setJobId] = useState<string | null>(null)
  const [evidenceTopK, setEvidenceTopK] = useState(5)
  const [pairThreshold, setPairThreshold] = useState(0.75)
  const [nliEnabled, setNliEnabled] = useState(false)
  const [nliThreshold, setNliThreshold] = useState(0.85)
  const [provider, setProvider] = useState("")
  const [model, setModel] = useState("")

  const ingest = useIngestPaper()
  const ingestUrl = useIngestUrl()
  const submitJob = useSubmitVerifyJob()
  const { data: job } = useJob(jobId)

  function addFiles(files: FileList | null) {
    if (!files) {
      return
    }

    const items = Array.from(files)
      .filter((file) => file.name.toLowerCase().endsWith(".pdf"))
      .map((file) => ({
        id: crypto.randomUUID(),
        label: file.name,
        file,
      }))

    setQueue((current) => [...current, ...items])
  }

  async function handleAddArxiv() {
    const url = arxivUrl.trim()

    if (!url) {
      toast.error("Enter an arXiv link or id (e.g. 2310.12345).")
      return
    }

    try {
      const ingested = await ingestUrl.mutateAsync({ url })
      const library = await fetchPapers()
      const saved = library.find(
        (paper) => paper.paper_id === ingested.paper_id,
      )

      setQueue((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          label: saved?.title ?? url,
          ingested: { paperId: ingested.paper_id },
        },
      ])
      setArxivUrl("")
      toast.success("Paper ingested — added to the queue.")
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Request failed.")
    }
  }

  async function handleRun() {
    if (queue.length === 0) {
      toast.error("Add at least one paper to the queue.")
      return
    }

    try {
      const papers: VerifyPaperInput[] = []

      const ingestedIds = queue
        .map((item) => item.ingested?.paperId)
        .filter((id): id is string => Boolean(id))
      const library =
        ingestedIds.length > 0 ? await fetchPapers() : []

      for (const item of queue) {
        if (item.file) {
          const paperId = `paper-${crypto.randomUUID().slice(0, 12)}`

          const upload = new FormData()

          upload.append("file", item.file)
          upload.append("paper_id", paperId)

          await ingest.mutateAsync(upload)

          const saved = library.find(
            (paper) => paper.paper_id === paperId,
          )

          papers.push({
            paper_path:
              saved?.path ?? `data/in/${paperId}_${item.file.name}`,
            paper_id: paperId,
          })
        } else if (item.ingested) {
          const saved = library.find(
            (paper) => paper.paper_id === item.ingested?.paperId,
          )

          if (!saved) {
            throw new Error(
              `Ingested paper not found in library: ${item.label}`,
            )
          }

          papers.push({
            paper_path: saved.path,
            paper_id: saved.paper_id,
          })
        }
      }

      const submitted = await submitJob.mutateAsync({
        papers,
        evidence_top_k: evidenceTopK,
        pair_threshold: pairThreshold,
        nli_threshold: nliEnabled ? nliThreshold : null,
        ...(provider ? { provider } : {}),
        ...(model ? { model } : {}),
      })

      setJobId(submitted.job_id)
      setQueue([])
      toast.success(`Batch of ${papers.length} started.`)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Request failed.")
    }
  }

  const busy =
    ingest.isPending || ingestUrl.isPending || submitJob.isPending

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <h1 className="text-2xl font-bold">Batch verify</h1>

      <Card>
        <CardHeader>
          <CardTitle>Paper queue</CardTitle>

          <CardDescription>
            Add PDFs or paste an arXiv link — metadata is read from each
            paper's content — then run the batch.
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Button
              type="button"
              size="sm"
              variant={sourceMode === "upload" ? "default" : "outline"}
              onClick={() => setSourceMode("upload")}
            >
              Upload PDFs
            </Button>

            <Button
              type="button"
              size="sm"
              variant={sourceMode === "arxiv" ? "default" : "outline"}
              onClick={() => setSourceMode("arxiv")}
            >
              From arXiv
            </Button>
          </div>

          {sourceMode === "upload" ? (
            <Input
              type="file"
              accept=".pdf,application/pdf"
              multiple
              onChange={(event) => addFiles(event.target.files)}
            />
          ) : (
            <div className="flex gap-2">
              <Input
                value={arxivUrl}
                onChange={(event) => setArxivUrl(event.target.value)}
                placeholder="https://arxiv.org/abs/2310.12345"
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.preventDefault()
                    void handleAddArxiv()
                  }
                }}
              />

              <Button
                type="button"
                variant="outline"
                onClick={() => void handleAddArxiv()}
                disabled={ingestUrl.isPending}
              >
                Add to queue
              </Button>
            </div>
          )}

          {queue.map((item) => (
            <div
              key={item.id}
              className="flex items-center justify-between rounded-lg border p-3"
            >
              <p className="truncate text-sm font-medium">{item.label}</p>

              <div className="flex shrink-0 items-center gap-2">
                <span className="text-xs text-muted-foreground">
                  {item.ingested ? "arXiv" : "PDF"}
                </span>

                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() =>
                    setQueue((current) =>
                      current.filter((entry) => entry.id !== item.id),
                    )
                  }
                >
                  <X className="size-4" />
                </Button>
              </div>
            </div>
          ))}

          <Button onClick={handleRun} disabled={busy}>
            Run verification ({queue.length})
          </Button>
        </CardContent>
      </Card>

      <OptionsPanel
        evidenceTopK={evidenceTopK}
        setEvidenceTopK={setEvidenceTopK}
        pairThreshold={pairThreshold}
        setPairThreshold={setPairThreshold}
        nliEnabled={nliEnabled}
        setNliEnabled={setNliEnabled}
        nliThreshold={nliThreshold}
        setNliThreshold={setNliThreshold}
        provider={provider}
        setProvider={setProvider}
        model={model}
        setModel={setModel}
      />

      {jobId ? <JobProgress job={job} /> : null}
    </div>
  )
}
