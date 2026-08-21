import { useEffect, useState } from "react"

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query"

import { api } from "@/api/client"
import type {
  AgreementStats,
  BenchmarkResult,
  ClaimDetailResponse,
  ClaimSummary,
  DebateRecord,
  HealthResponse,
  IngestUrlRequest,
  IngestUrlResponse,
  JobRecord,
  LLMConfigRequest,
  LLMConfigResponse,
  OverrideRecord,
  PaperBlocksResponse,
  PaperSummary,
  ReportResponse,
  VerifyJobRequest,
} from "@/api/types"

const ACTIVE_STATUSES = new Set(["queued", "running"])

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: () => api.get<HealthResponse>("/health"),
    refetchInterval: 30_000,
  })
}

export function usePapers() {
  return useQuery({
    queryKey: ["papers"],
    queryFn: () => api.get<PaperSummary[]>("/papers"),
  })
}

export function useAllClaims() {
  return useQuery({
    queryKey: ["claims"],
    queryFn: () => api.get<ClaimSummary[]>("/claims"),
    staleTime: 30_000,
  })
}

export function fetchPapers(): Promise<PaperSummary[]> {
  return api.get<PaperSummary[]>("/papers")
}

export function useJob(jobId: string | null) {
  const [job, setJob] = useState<JobRecord | undefined>(undefined)

  useEffect(() => {
    if (!jobId) {
      setJob(undefined)
      return
    }

    let source: EventSource | null = null
    let cancelled = false
    let retries = 0
    let lastStatus: string | null = null
    let retryTimer: number | null = null

    const connect = () => {
      source = new EventSource(`/jobs/${jobId}/events`)

      source.onmessage = (event) => {
        if (cancelled) {
          return
        }

        try {
          const record = JSON.parse(event.data) as JobRecord

          lastStatus = record.status
          setJob(record)
        } catch {
          // ignore malformed frames
        }
      }

      source.onerror = () => {
        source?.close()

        // the server closes the stream once the job finishes; only
        // reconnect while the job was still active
        if (
          cancelled ||
          retries >= 3 ||
          (lastStatus !== null && !ACTIVE_STATUSES.has(lastStatus))
        ) {
          return
        }

        retries += 1
        retryTimer = window.setTimeout(connect, 1_000)
      }
    }

    connect()

    return () => {
      cancelled = true

      if (retryTimer !== null) {
        window.clearTimeout(retryTimer)
      }

      source?.close()
    }
  }, [jobId])

  return { data: job, isLoading: jobId !== null && job === undefined }
}

export function useReport(paperId: string) {
  return useQuery({
    queryKey: ["report", paperId],
    queryFn: () => api.get<ReportResponse>(`/report/${paperId}`),
  })
}

export function useClaim(claimId: string) {
  return useQuery({
    queryKey: ["claim", claimId],
    queryFn: () => api.get<ClaimDetailResponse>(`/claims/${claimId}`),
  })
}

export function usePaperBlocks(paperId: string) {
  return useQuery({
    queryKey: ["paper-blocks", paperId],
    queryFn: () =>
      api.get<PaperBlocksResponse>(`/papers/${paperId}/blocks`),
  })
}

export function useDebate(claimId: string) {
  return useQuery({
    queryKey: ["debate", claimId],
    queryFn: () => api.get<DebateRecord>(`/claims/${claimId}/debate`),
    retry: false,
  })
}

export function useRunDebate(claimId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () =>
      api.post<DebateRecord>(`/claims/${claimId}/debate`, {}),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["debate", claimId],
      })
    },
  })
}

export function useOverrideVerdict(claimId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (request: { verdict: string; note?: string }) =>
      api.post<OverrideRecord>(`/claims/${claimId}/override`, request),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["claim", claimId] })
      void queryClient.invalidateQueries({ queryKey: ["report"] })
      void queryClient.invalidateQueries({ queryKey: ["agreement"] })
    },
  })
}

export function useFlagReview() {
  return useMutation({
    mutationFn: ({
      flagId,
      accepted,
    }: {
      flagId: string
      accepted: boolean
    }) => api.post(`/flags/${flagId}/review`, { accepted }),
  })
}

export function useAgreementStats() {
  return useQuery({
    queryKey: ["agreement"],
    queryFn: () => api.get<AgreementStats>("/stats/agreement"),
  })
}

export function useConfig() {
  return useQuery({
    queryKey: ["config"],
    queryFn: () => api.get<LLMConfigResponse>("/api/config"),
  })
}

export function useIngestPaper() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (form: FormData) =>
      api.postForm<{ paper_id: string }>("/ingest", form),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["papers"] })
    },
  })
}

export function useIngestUrl() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (request: IngestUrlRequest) =>
      api.post<IngestUrlResponse>("/ingest/url", request),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["papers"] })
    },
  })
}

export function useSubmitVerifyJob() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (request: VerifyJobRequest) =>
      api.post<{ job_id: string }>("/verify/jobs", request),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["jobs"] })
    },
  })
}

export function useSubmitBenchmarkJob() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (request: { split: string; threshold: number }) =>
      api.post<{ job_id: string }>("/benchmark/scifact/jobs", request),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["jobs"] })
    },
  })
}

export function useSaveConfig() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (request: LLMConfigRequest) =>
      api.post<LLMConfigResponse>("/api/config", request),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["config"] })
    },
  })
}

export function useClearConfig() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => api.del<{ status: string }>("/api/config"),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["config"] })
    },
  })
}

export function benchmarkResultFromJob(
  job: JobRecord | undefined,
): BenchmarkResult | null {
  if (!job || job.status !== "done" || !job.results?.length) {
    return null
  }

  return job.results[0] as BenchmarkResult
}
