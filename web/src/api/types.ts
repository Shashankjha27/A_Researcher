export type JobStatus = "queued" | "running" | "done" | "error"

export type Verdict =
  | "supported"
  | "provisionally_supported"
  | "contradicted"
  | "conflicting"
  | "insufficient"

export type Relation = "contradiction" | "support" | "neutral"

export interface PaperSummary {
  paper_id: string
  title: string
  authors: string[]
  year: number
  path: string
  funding_source: string | null
  retraction_status: string
  claim_count: number
}

export interface ClaimSummary {
  claim_id: string
  paper_id: string
  claim_text: string
  verdict: Verdict | null
}

export interface FlagItem {
  flag_type?: string
  severity?: string
  rationale_string?: string
  [key: string]: unknown
}

export interface EvidenceItem {
  paper_id?: string
  text: string
  score: number
}

export interface ClaimRecord {
  claim_id: string
  paper_id: string
  claim_text: string
  effect_direction?: string
  method_type?: string
  sample_size?: number | null
  source_sentence?: string
  start_offset?: number
  end_offset?: number
  confidence_score?: number
  confidence_components?: Record<string, number>
  verdict?: Verdict
  support_count?: number
  contradiction_count?: number
  flags?: FlagItem[]
  supporting_evidence?: EvidenceItem[]
  contradicting_evidence?: EvidenceItem[]
  override?: OverrideRecord | null
}

export interface OverrideRecord {
  override_id: string
  claim_id: string
  paper_id: string
  original_verdict: Verdict | null
  overridden_verdict: Verdict
  note: string | null
  created_at: string
}

export interface AgreementStats {
  total_verdicts: number
  overridden: number
  accept_rate: number | null
}

export interface ClaimSide {
  claim_id: string
  paper_id: string
  claim_text: string
  source_sentence: string | null
}

export interface ContradictionItem {
  pair_id: string
  nli_probability: number
  threshold: number
  checked_at: string
  claim_a: ClaimSide | null
  claim_b: ClaimSide | null
}

export interface ReportResponse {
  paper_id: string
  report: string
  claims: ClaimRecord[]
  contradictions: ContradictionItem[]
  nli_model?: string
}

export interface PairVerdict {
  pair_id: string
  claim_id_a: string
  claim_id_b: string
  relation: Relation
  confidence_score: number
  nli_probability: number
  nli_model: string
  threshold: number
  checked_at: string
}

export interface ClaimDetailResponse {
  claim: ClaimRecord
  linked_verdicts: PairVerdict[]
}

export interface JobProgress {
  done: number
  total: number
  stage: string | null
}

export interface VerifyJobResult {
  paper: { paper_id: string; title?: string }
  claims: ClaimRecord[]
  pair_verdicts: unknown[]
  report: string
}

export interface BenchmarkLabelRow {
  label: string
  precision: number
  recall: number
  f1: number
}

export interface BenchmarkResult {
  split: string
  threshold: number
  nli_model?: string
  claims_count: number
  labels: BenchmarkLabelRow[]
  macro: { precision: number; recall: number; f1: number }
}

export interface JobRecord {
  job_id: string
  kind: "verify" | "benchmark"
  status: JobStatus
  progress: JobProgress
  results: unknown[] | null
  error: string | null
  created_at: string
}

export type LLMProvider = "openai" | "gemini" | "claude" | "ollama"

export interface LLMConfigResponse {
  provider: string | null
  model: string | null
  has_key: boolean
  configured: boolean
}

export interface LLMConfigRequest {
  provider: LLMProvider
  model: string
  api_key?: string | null
}

export interface HealthResponse {
  status: string
  models: Record<string, unknown>
}

export interface VerifyPaperInput {
  paper_path: string
  paper_id: string
  title?: string | null
  authors?: string[]
  year?: number | null
}

export interface VerifyJobRequest {
  papers: VerifyPaperInput[]
  provider?: string | null
  model?: string | null
  api_key?: string | null
  evidence_top_k?: number
  pair_threshold?: number
  nli_threshold?: number | null
}

export interface IngestUrlRequest {
  url: string
  paper_id?: string
}

export interface IngestUrlResponse {
  paper_id: string
}

export interface PaperBlock {
  section: string
  text: string
  start_offset: number
  end_offset: number
}

export interface PaperBlocksResponse {
  paper_id: string
  title: string
  blocks: PaperBlock[]
}

export interface DebateTurn {
  role: "defender" | "attacker" | "judge"
  text: string
}

export interface DebateRecord {
  debate_id: string
  claim_id: string
  paper_id: string
  model: string
  rounds: number
  turns: DebateTurn[]
  judge_verdict: Verdict
  judge_rationale: string
  created_at: string
}
