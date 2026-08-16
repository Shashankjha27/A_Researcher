# A_Researcher

#### Not Summarizing, but Cross-examining papers!

Given a paper or a collection of papers on the same topic, and it extracts the empirical claims made in them  and then identifies supporting claims and contradictions (if any) using an NLI model (not simply repurposed or specialized LLM).

Flag the threats to validity which a careful reviewer will look for, and hand back a confidence-score report with claims linked to the exact sentences they came from.

## The Problem

As AI models have become increasingly general-purpose,  they often lack in the same things.For example , Generalization can come at the expense of depth and reliability in specific tasks.

Ask any LLM to summarize what the research paper says about something, and it will respond with confidence with an answer comprising of assortment of actual truth of the paper, supporting findings, contradictory statements, and not to mention if any - hallucinations, with no way to tell them apart. 

LLM, Hardware and Agents deployed for all intents and purposes only change how **Educated** the **Guess** is.

## What This Does Instead

1. **EXTRACT** - Pull individual claims out of papers as structured data.
2. **VERIFY** - Run all claims by a pre-trained **NLI classifier** (`entailment / contradiction / neutral`), and benchmark against **SciFact**.
3. **FLAG** - Rules-based integrity checks.
4. **SCORE** - Transparent, deterministic, confidence formula.
5. **SYNTHESIZE** - A structured report per subtopic - support, dissent, flags, verdict, with exact sources.

## Key Point
Contradiction detection is an NLI classifier and never an LLM prompt. That's what makes this benchmarkable, and it's the whole reason this isn't just another summarizer wrapper.



## Architecture

```mermaid
flowchart LR
  A[Papers:PDF/txt/md] --> B[Ingest and Chunk<br/>sentence offsets kept]
  B --> C[Extracts claims<br/>LLM + JSON schema gate]
  C --> D[NLI contradiction engine<br/> benchmarked on SciFact]
  D --> E[Integrity flags<br/>pure rule functions]
  E --> F[Confidence score<br/> pure functions]
  F --> G[Synthesis report<br/>grouped by sub-topic]
  C -.source_sentence.-> G
```
One monolithic FastAPI service.
JSONL document store, No queues, No vector DB, No training - inference only.

---
## TECH STACK

| Layer | Choice | Why |
|---|---|---|
| Backend | FastAPI + Pydantic v2 | Free Interactive API docs, schema gate for LLM output |
|Contradiction Detection | Pretrained NLI classifier (DeBERTa-v3 zeroshot / SciFact-tuned)| Deterministic, Benchmarkable, \~500mb |
Pair Reduction|all-MiniLM-L6-v2 embeddings + clustering|O(n²) → tractable |
Claim extraction |LLM  (API/Local)+ Json Schema gate retry <= 2|Judgement Task, but shape is guaranteed automatically|
|Scoring and Flags|Pure Python functions|Explainable, zero LLM guessing|
|Storage|JSONL|Prototype scope|


## AI TRANSPARENCY

This project is created by humans and not by AI; however ,AI is used in assistance for the work. There is no block of code or concept used in this project that is not human-reviewed and role of the AI is strictly limited to assistance rather than taking responsibility itself.
