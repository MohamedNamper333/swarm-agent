# Swarm Enterprise Roadmap v4 — 50-Agent Multi-Tier Architecture

**Last Updated**: 2026-08-10
**Status**: PLAN MODE → awaiting approval to execute Phase 1
**Owner**: Architecture team
**Target**: Production-ready 50-agent enterprise swarm on NVIDIA NIM (free tier)

---

## 1. Executive Summary

This roadmap details the phased rollout of a 50-agent enterprise swarm
across 4 tiers (Board, C-Suite, Directors, Workers) using only free-tier
NVIDIA NIM models. Total cost: $0/month. Phasing: 3 phases × 4 weeks each.

### Key Constraints
- All models free (NVIDIA NIM trial tier, rate-limited)
- 3-level fallback chain per premium role
- Redis caching on :27123
- Inline safety filter (<100ms overhead)
- Daily circuit breaker at 80% of model quota

### Key Decisions
- Hybrid safety layer (inline light + on-demand heavy)
- Phased rollout: 16 → 29 → 50 agents
- Voice dept DELETED (no chat model on NIM)
- Knowledge dept ADDED (4 agents for embeddings/RAG)
- Safety dept ADDED (3 agents + inline filters)
- opencode zen 8 free models = DEV ONLY

---

## 2. Architecture Overview

### 2.1 Tiers
┌─────────────────────────────────────────────┐ │ TIER 1: BOARD (5 agents) │ │ Decisions, strategy, ethics VETO, risk │ ├─────────────────────────────────────────────┤ │ TIER 2: C-SUITE (7 agents) │ │ CEO, CTO, CFO, COO, CMO, CHRO, CLO │ │ CLO has legal VETO (Nemotron Ultra) │ ├─────────────────────────────────────────────┤ │ TIER 3: DIRECTORS (8 agents) │ │ One per department: code, design, video, │ │ research, data, language, knowledge, safety│ ├─────────────────────────────────────────────┤ │ TIER 4: WORKERS (30 agents) │ │ 6 code + 7 design + 5 video + 3 research │ │ + 2 data + 2 language + 4 knowledge + 3 safety│ ├─────────────────────────────────────────────┤ │ INFRASTRUCTURE │ │ - Inline safety filter (Nemotron-3.5) │ │ - Redis cache (:27123) │ │ - Fallback chains (3 levels) │ │ - Circuit breaker (80% daily limit) │ │ - Rate limiter per model │ └─────────────────────────────────────────────┘


### 2.2 Department Breakdown

| # | Department | Director Model | Workers | Total |
|---|---|---|---|---|
| 1 | Board | (5 separate roles) | — | 5 |
| 2 | C-Suite | (7 separate roles) | — | 7 |
| 3 | Code | nemotron-3-super-120b-a12b | 6 | 7 |
| 4 | Design | moonshotai/kimi-k2.5 | 7 | 8 |
| 5 | Video | minimaxai/minimax-m3 | 5 | 6 |
| 6 | Research | openai/gpt-oss-120b | 3 | 4 |
| 7 | Data | google/gemma-3-27b-it | 2 | 3 |
| 8 | Language | z-ai/glm5.1 | 2 | 3 |
| 9 | Knowledge | nvidia/llama-3.2-nv-embedqa-1b-v2 | 4 | 5 |
| 10 | Safety | nvidia/nvidia-nemotron-nano-9b-v2 | 3 | 4 |
| **TOTAL** | | | **30** | **50** |

---

## 3. Tier 1: Board (5 agents)

| Role | Primary | Fallback 1 | Fallback 2 | VETO? |
|---|---|---|---|---|
| chairman | deepseek-v4-pro | deepseek-v4-flash | z-ai/glm5.1 | tiebreaker |
| strategy_advisor | openai/gpt-oss-120b | openai/gpt-oss-20b | nemotron-3-super-120b | no |
| ethics_advisor | nemotron-3-ultra-550b-a55b | nemotron-3-super-120b | llama-3.3-nemotron-super-49b | **YES** |
| risk_advisor | nemotron-3-super-120b-a12b | llama-3.3-nemotron-super-49b | nemotron-3-nano-30b | no |
| user_advisor | moonshotai/kimi-k2.5 | llama-3.2-11b-vision | kimi-k2-instruct | no |

**Note**: chairman only votes on tie. ethics_advisor has absolute VETO on
content involving PII, harm, or illegal activity.

---

## 4. Tier 2: C-Suite (7 agents)

| Role | Primary | Fallback 1 | Fallback 2 | Budget |
|---|---|---|---|---|
| CEO | deepseek-v4-pro | deepseek-v4-flash | z-ai/glm5.1 | 200K/project |
| CTO | nemotron-3-super-120b-a12b | llama-3.3-nemotron-super-49b | nemotron-3-nano-30b | 200K |
| CFO | mistral-small-4-119b | mistral-nemotron | nemotron-mini-4b | 200K |
| COO | llama-3.3-nemotron-super-49b | nemotron-3-super-120b | nemotron-3-nano-30b | 200K |
| CMO | moonshotai/kimi-k2.5 | llama-3.2-11b-vision | kimi-k2-instruct | 200K |
| CHRO | z-ai/glm5.1 | qwen3-next-80b-a3b | nemotron-mini-4b | 200K |
| CLO | nemotron-3-ultra-550b-a55b | nemotron-3-super-120b | llama-3.3-nemotron-super-49b | **VETO** |

**CFO circuit breaker**: 80% of daily limit = auto-halt non-critical calls.

---

## 5. Tier 3 + 4: Departments + Workers

### 5.1 Code Dept (7 total: 1 director + 6 workers)

| Role | Primary | Fallback 1 | Fallback 2 |
|---|---|---|---|
| director | nemotron-3-super-120b-a12b | llama-3.3-nemotron-super-49b | nemotron-3-nano-30b |
| architect | nemotron-3-super-120b-a12b | llama-3.3-nemotron-super-49b | nemotron-3-nano-30b |
| coder_1 | qwen2.5-coder-32b-instruct | qwen3-coder-480b | qwq-32b |
| coder_2 | qwen3-coder-480b-a35b-instruct | qwen2.5-coder-32b | qwq-32b |
| code_reviewer | nemotron-3-ultra-550b-a55b | nemotron-3-super-120b | llama-3.3-nemotron-super-49b |
| qa_engineer | nemotron-3-nano-30b-a3b | nemotron-mini-4b | nvidia-nemotron-nano-9b-v2 |
| devops | llama-3.3-70b-instruct | llama-3.1-70b | nemotron-3-super-120b |

### 5.2 Design Dept (8 total: 1 director + 7 workers)

| Role | Primary | Fallback 1 | Fallback 2 |
|---|---|---|---|
| director | moonshotai/kimi-k2.5 | llama-3.2-11b-vision | kimi-k2-instruct |
| image_gen_1 (quality) | black-forest-labs/flux.1-dev | flux.2-klein-4b | stabilityai/sdxl |
| image_gen_2 (speed) | black-forest-labs/flux.2-klein-4b | flux.1-schnell | flux.1-dev |
| designer_1 | thinking machines/inkling | kimi-k2.5 | deepseek-v4-flash |
| designer_2 | thinking machines/inkling | kimi-k2.5 | deepseek-v4-flash |
| ux_specialist | moonshotai/kimi-k2.5 | llama-3.2-11b-vision | kimi-k2-instruct |
| 3d_designer_1 | microsoft/trellis | minimaxai/minimax-m3 | (no fallback) |
| 3d_designer_2 | microsoft/trellis | minimaxai/minimax-m3 | (no fallback) |

### 5.3 Video Dept (6 total: 1 director + 5 workers)

| Role | Primary | Fallback 1 | Fallback 2 |
|---|---|---|---|
| director | minimaxai/minimax-m3 | kimi-k2.5 | llama-3.2-11b-vision |
| video_gen_1 | nvidia/cosmos-predict1-7b | stabilityai/stable-video-diffusion | (no fallback) |
| video_gen_2 | stabilityai/stable-video-diffusion | cosmos-predict1-7b | (no fallback) |
| animator_1 | minimaxai/minimax-m3 | kimi-k2.5 | gemma-3-27b-it |
| animator_2 | minimaxai/minimax-m3 | kimi-k2.5 | gemma-3-27b-it |
| motion_designer | mistral-medium-3.5-128b | gemma-3-27b-it | nemotron-mini-4b |

### 5.4 Research Dept (4 total: 1 director + 3 workers)

| Role | Primary | Fallback 1 | Fallback 2 |
|---|---|---|---|
| director | openai/gpt-oss-120b | openai/gpt-oss-20b | nemotron-3-super-120b |
| researcher_1 | openai/gpt-oss-120b | nemotron-3-super-120b | deepseek-v4-flash |
| researcher_2 | deepseek-v4-flash | nemotron-3-nano-30b | nemotron-mini-4b |
| fact_checker | nemotron-3-super-120b-a12b | llama-3.3-nemotron-super-49b | openai/gpt-oss-20b |

### 5.5 Data Dept (3 total: 1 director + 2 workers)

| Role | Primary | Fallback 1 | Fallback 2 |
|---|---|---|---|
| director | google/gemma-3-27b-it | gemma-3n-e4b-it | nemotron-3-nano-30b |
| data_analyst | gemma-3-27b-it | nemotron-3-nano-30b | nemotron-mini-4b |
| data_engineer | nemotron-3-nano-30b-a3b | nemotron-mini-4b | nvidia-nemotron-nano-9b-v2 |

### 5.6 Language Dept (3 total: 1 director + 2 workers)

| Role | Primary | Fallback 1 | Fallback 2 |
|---|---|---|---|
| director | z-ai/glm5.1 | z-ai/glm4.7 | z-ai/glm-5.2 |
| translator | nvidia/riva-translate-4b-instruct-v2 | riva-translate-4b-v1.1 | z-ai/glm5.1 |
| localizer | z-ai/glm5.1 | z-ai/glm-5.2 | sarvam-m |

### 5.7 Knowledge Dept (5 total: 1 director + 4 workers)

| Role | Primary | Fallback 1 | Fallback 2 |
|---|---|---|---|
| director | nvidia/llama-3.2-nv-embedqa-1b-v2 | nvidia/llama-3.2-nemoretriever-1b-vlm-embed-v1 | nemoretriever-300m-embed-v2 |
| knowledge_curator | baai/bge-m3 | nvidia/nv-embed-v1 | nemoretriever-300m-embed-v2 |
| rag_retriever | nemoretriever-300m-embed-v2 | nemoretriever-1b-vlm-embed-v1 | llama-3.2-nv-embedqa-1b-v2 |
| rag_reranker | nemoretriever-500m-rerank-v2 | llama-3.2-nv-rerankqa-1b-v2 | nemoretriever-ocdr-1b-v1 |
| doc_parser | nemoretriever-parse | nemotron-parse | (no fallback) |

### 5.8 Safety Dept (4 total: 1 director + 3 workers + inline filters)

| Role | Primary | Fallback 1 | Fallback 2 |
|---|---|---|---|
| director (orchestrator) | nvidia-nemotron-nano-9b-v2 | nemotron-mini-4b | nemotron-3-nano-30b |
| content_safety_analyst | llama-3.1-nemoguard-8b-content-safety | nemotron-3.5-content-safety | nemotron-content-safety-reasoning-4b |
| topic_control_analyst | llama-3.1-nemoguard-8b-topic-control | nemotron-3-content-safety | nemotron-3.5-content-safety |
| jailbreak_analyst | nemoguard-jailbreak-detect | nemotron-content-safety-reasoning-4b | nemotron-3.5-content-safety |

**Inline filters** (transparent, every LLM call passes through):
- `nvidia/nemotron-3.5-content-safety` (output check)
- `nvidia/nemotron-content-safety-reasoning-4b` (input reasoning check)
- `nvidia/nemoguard-jailbreak-detect` (input jailbreak detect)

---

## 6. Phase 1: Foundation (W1-W4, 16 agents)

### 6.1 Weekly Breakdown

| Week | Deliverable | Tests |
|---|---|---|
| W1 | Board chairman + 4 advisors, inline safety filter wired | test_safety_layer, test_chairman |
| W2 | Knowledge Dept (4 workers + director), Redis cache | test_cache_manager, test_rag |
| W3 | Safety Dept (3 workers + director + orchestrator) | test_safety_dept |
| W4 | Integration tests, rate limit validation, dashboard | test_full_integration |

### 6.2 Acceptance Criteria

- [ ] 16 agents running concurrently
- [ ] Safety filter catches 95%+ of red team prompts
- [ ] Rate limits not breached in 24h stress test
- [ ] Cache hit rate > 40%
- [ ] Safety latency overhead < 100ms (p95)
- [ ] Board VETO logic works (ethics_advisor can block)
- [ ] Circuit breaker activates at 80% of daily limit

---

## 7. Phase 2: Operational Loop (W5-W8, 13 agents)

### 7.1 Weekly Breakdown

| Week | Deliverable | Tests |
|---|---|---|
| W5 | C-Suite (CEO, CTO, CFO, COO) | test_c_suite_basic |
| W6 | C-Suite (CMO, CHRO, CLO) + CFO budget tracker | test_cfo_circuit_breaker |
| W7 | Code Dept (architect, coder_1, coder_2) + Docker sandbox | test_code_sandbox |
| W8 | Code Dept (reviewer, QA, devops) + GitHub integration | test_code_dept_full |

### 7.2 Acceptance Criteria

- [ ] 13 new agents working
- [ ] Code sandbox isolates malicious code
- [ ] Fallback chain activates on 429 (mock test)
- [ ] CTO → Code Dept delegation works through Board VETO
- [ ] CFO budget dashboard shows $0 daily cost
- [ ] Code reviewer catches SQLi/XSS payloads
- [ ] Devops agent opens real PRs on GitHub
- [ ] 29-agent stress test: rate limits still OK

---

## 8. Phase 3: Content Departments (W9-W12, 21 agents)

### 8.1 Weekly Breakdown

| Week | Deliverable | Tests |
|---|---|---|
| W9 | Design Dept (director + 2 image_gen + 2 designer) | test_design_dept |
| W10 | Design Dept (ux_specialist + 2 3d_designer) | test_3d_workflow |
| W11 | Video Dept (director + 2 video_gen + 2 animator) + motion | test_video_dept |
| W12 | Research + Data + Language + final integration | test_full_50 |

### 8.2 Acceptance Criteria

- [ ] 21 new agents working
- [ ] Image generation produces valid PNGs (1024x1024)
- [ ] 3D models loadable (Trellis format)
- [ ] Video generation produces valid MP4s
- [ ] Multimodal agents (Kimi K2.5) accept image+text input
- [ ] 50-agent full swarm stress test (24h, no rate limit breach)
- [ ] All 50 agents in dashboard with health checks

---

## 9. Model Registry Contents (~50 unique models)

### 9.1 Frontier Reasoning (Premium: ~200/day)
- `nvidia/nemotron-3-ultra-550b-a55b` (550B total, 55B active, 1M ctx)
- `deepseek-ai/deepseek-v4-pro` (1.6T total, 49B active, 1M ctx)
- `moonshotai/kimi-k2.5` (multimodal)

### 9.2 Large Reasoning (~500/day)
- `nvidia/nemotron-3-super-120b-a12b`
- `nvidia/llama-3.3-nemotron-super-49b-v1.5`
- `nvidia/llama-3.1-nemotron-ultra-253b-v1`
- `openai/gpt-oss-120b`
- `meta/llama-3.3-70b-instruct`
- `z-ai/glm5.1`
- `mistralai/mistral-small-4-119b-2603`
- `mistralai/mistral-medium-3.5-128b`
- `qwen/qwen3-coder-480b-a35b-instruct`
- `qwen/qwen3-next-80b-a3b-instruct`

### 9.3 Medium (~1000/day)
- `deepseek-ai/deepseek-v4-flash`
- `meta/llama-3.1-70b-instruct`
- `meta/llama-3.2-11b-vision-instruct`
- `google/gemma-3-27b-it`
- `qwen/qwen2.5-coder-32b-instruct`
- `qwen/qwq-32b`
- `moonshotai/kimi-k2-instruct`
- `moonshotai/kimi-k2-thinking`
- `z-ai/glm4.7`
- `z-ai/glm-5.2`
- `mistralai/mistral-nemotron`
- `mistralai/mixtral-8x22b-instruct`
- `mistralai/ministral-14b-instruct-2512`
- `sarvamai/sarvam-m`
- `stepfun-ai/step-3.5-flash`
- `stepfun-ai/step-3.7-flash`
- `stockmark/stockmark-2-100b-instruct`
- `poolside/laguna-xs-2-1`
- `upstage/solar-10.7b-instruct`
- `thinking machines/inkling`
- `microsoft/phi-4-mini-instruct`
- `microsoft/phi-4-mini-flash-reasoning`
- `microsoft/phi-4-multimodal-instruct`
- `nvidia/llama-3.1-nemotron-nano-8b-v1`
- `nvidia/nvidia-nemotron-nano-9b-v2`
- `google/gemma-3n-e4b-it`
- `google/codegemma-7b`
- `google/diffusiongemma-26b-a4b-it`
- `google/paligemma`
- `google/gemma-7b`
- `meta/llama-3.2-1b-instruct`
- `meta/llama-3.2-3b-instruct`
- `meta/llama-3.1-8b-instruct`
- `meta/llama2-70b`

### 9.4 Small / Nano (~5000/day)
- `nvidia/nemotron-3-nano-30b-a3b`
- `nvidia/nemotron-mini-4b-instruct`
- `nvidia/nemotron-content-safety-reasoning-4b`
- `nvidia/nvidia-nemotron-nano-9b-v2`
- `nvidia/riva-translate-4b-instruct-v1.1`
- `nvidia/riva-translate-4b-instruct-v2`
- `meta/llama-3.2-1b-instruct`
- `openai/gpt-oss-20b`

### 9.5 Safety Models (inline + department)
- `nvidia/nemotron-3.5-content-safety` (inline output)
- `nvidia/nemotron-3-content-safety` (inline)
- `nvidia/nemotron-content-safety-reasoning-4b` (inline input)
- `nvidia/llama-3.1-nemoguard-8b-content-safety`
- `nvidia/llama-3.1-nemoguard-8b-topic-control`
- `nvidia/nemoguard-jailbreak-detect`
- `nvidia/llama-3.1-nemotron-safety-guard-8b-v3`

### 9.6 Visual / Image Generation
- `black-forest-labs/flux.1-dev` (non-commercial, quality)
- `black-forest-labs/flux.1-schnell` (speed)
- `black-forest-labs/flux.2-klein-4b` (small/fast)
- `black-forest-labs/flux.1-kontext-dev` (multimodal)
- `stabilityai/stable-diffusion-3-medium`
- `stabilityai/stable-diffusion-xl`
- `stabilityai/stable-video-diffusion` (video)

### 9.7 3D / Video
- `microsoft/trellis` (3D)
- `nvidia/cosmos-predict1-7b` (image-to-video)
- `nvidia/cosmos-predict1` (other variants)
- `nvidia/sparsedrive`
- `nvidia/streampetr`
- `nvidia/bevformer`
- `nvidia/visual-changenet`

### 9.8 Retrieval / Embeddings
- `baai/bge-m3`
- `nvidia/nv-embed-v1` (873M)
- `nvidia/nv-embedcode-7b-v1`
- `nvidia/nv-embedqa-e5-v5`
- `nvidia/llama-nemotron-embed-1b-v2`
- `nvidia/llama-nemotron-embed-vl-1b-v2`
- `nvidia/llama-nemotron-rerank-1b-v2`
- `nvidia/llama-nemotron-rerank-vl-1b-v2`
- `nvidia/llama-3.2-nv-embedqa-1b-v2`
- `nvidia/llama-3.2-nv-rerankqa-1b-v1`
- `nvidia/llama-3.2-nv-rerankqa-1b-v2`
- `nvidia/llama-3.2-nemoretriever-1b-vlm-embed-v1`
- `nvidia/llama-3.2-nemoretriever-300m-embed-v1`
- `nvidia/llama-3.2-nemoretriever-300m-embed-v2`
- `nvidia/llama-3.2-nemoretriever-500m-rerank-v2`
- `nvidia/llama-3.2-nemoretriever-ocdr-1b-v1` (OCR)
- `nvidia/nemotron-3-embed-1b`
- `nvidia/nemoretriever-parse` (PDF/DOCX parser)
- `nvidia/nemotron-parse`
- `nvidia/nemoretriever-table-structure-v1`
- `nvidia/nemoretriever-chart-element-v1`
- `nvidia/nvclip` (image embeddings)
- `nvidia/embed-qa-4`
- `nvidia/rerank-qa-mistral-4b`
- `nvidia/nv-rerankqa-mistral-4b-v3`
- `snowflake/arctic-embed-l`

### 9.9 Other / Specialized
- `nvidia/gliner-pii` (PII detection)
- `nvidia/usdcode`
- `meta/llama-guard-4-12b`
- `nvidia/llama-3.1-nemotron-nano-vl-8b-v1`
- `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`
- `nvidia/nemotron-nano-12b-v2-vl`
- `nvidia/nemotron-3.5-content-safety`
- `nvidia/nemotron-3-content-safety`
- `nvidia/vila`
- `nvidia/nv-dinov2`
- `nvidia/nv-grounding-dino`
- `nvidia/ising-calibration-1.5-31b`
- `nvidia/retail-object-detection`
- `hive/ai-generated-image-detection`
- `hive/deepfake-image-detection`

**Total unique models**: ~75 (across all tiers)

---

## 10. Infrastructure Components

### 10.1 Redis Cache (`:27123`)
- TTL: 1h for factual queries, 24h for static content
- Hit rate target: > 40%
- Keys: `swarm:cache:{agent_id}:{hash(query)}`

### 10.2 Fallback Chain Logic
- Try primary → on 429/timeout (3 retries) → fallback 1
- Fallback 1 → on same error → fallback 2
- Fallback 2 → on same error → 503 to caller
- Each fallback has 5s timeout

### 10.3 Circuit Breaker
- Per-model daily counter (resets at 00:00 UTC)
- Trigger: 80% of estimated daily limit
- Action: queue requests, do not send until next day
- Logs: `swarm:circuit:{model}:{date}`

### 10.4 Inline Safety Filter
- Order: jailbreak_detect → content_safety → reasoning_safety
- Latency target: < 100ms (p95)
- Bypass: only for internal-to-internal calls (config flag)

### 10.5 Rate Limiter
- Per-model daily counter
- Per-model concurrent limit (max 10 in flight)
- 429 response → auto fallback
- Daily reset at 00:00 UTC

---

## 11. File Structure

### 11.1 New Files (Phase 1)
swarm/enterprise/ ├── board/ │ ├── chairman.py │ ├── strategy_advisor.py │ ├── ethics_advisor.py │ ├── risk_advisor.py │ └── user_advisor.py ├── knowledge/ │ ├── curator.py │ ├── retriever.py │ ├── reranker.py │ └── doc_parser.py ├── safety/ │ ├── content_safety.py │ ├── topic_control.py │ ├── jailbreak_detect.py │ └── orchestrator.py ├── core/ │ ├── model_registry.py (extend from 6 → ~50) │ ├── fallback_chain.py │ ├── circuit_breaker.py │ ├── rate_limiter.py │ ├── cache_manager.py │ └── safety_filter.py (inline)

swarm/integrations/ ├── nvidia_nim.py (OpenAI-compat client) ├── opencode_zen.py (dev-only fallback) └── safety_filter.py

tests/ ├── test_safety_layer.py ├── test_fallback_chain.py ├── test_circuit_breaker.py ├── test_rate_limit.py └── test_board.py

configs/ ├── production.json (50 models, free tier only) ├── development.json (+ opencode zen enabled) └── phase1.json (16 agents only)


### 11.2 Modified Files
- `swarm/core/model_registry.py` (extend DEFAULT_MODELS)
- `swarm/core/agent_router.py` (add fallback chain)
- `swarm/core/agent_state_machine.py` (add VETO state)
- `swarm/api/rest_server.py` (add /veto, /budget endpoints)
- `swarm/resilience/rate_limiter.py` (per-model tuning)
- `swarm/resilience/task_queue.py` (priority queue)

---

## 12. Cost Analysis

### 12.1 Monthly Cost Breakdown
| Component | Cost |
|---|---|
| NVIDIA NIM API | $0 (free tier) |
| Redis (local) | $0 |
| Docker sandbox | $0 |
| opencode zen (dev) | $0 |
| **TOTAL** | **$0/month** |

### 12.2 Free Tier Limits (estimated daily)
- Premium (~200/day): 250 req/day actual usage = OK
- Large (~500/day): 500 req/day = OK
- Medium (~1000/day): 1500 req/day = OK
- Small (~5000/day): 2500 req/day = OK

### 12.3 Scaling Beyond Free Tier
- Upgrade to NVIDIA AI Enterprise (~$4500/year per GPU)
- Or self-host NIM containers on owned GPUs (4xB200 minimum for Ultra)
- Estimated self-host cost: $30K/month for 4xB200 cluster

---

## 13. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Rate limit hit mid-task | High | Fallback chain + queueing |
| Premium model 429 | Medium | Fallback to medium tier |
| Cache stampede | Medium | Cache stampede protection (lock) |
| Safety filter bypass | Critical | Defense-in-depth (inline + dept) |
| CLO VETO deadlock | High | Timeout + auto-escalate to chairman |
| Code sandbox escape | Critical | Docker isolation + read-only fs + no network |
| Daily circuit breaker | Medium | Auto-resume next day + notification |
| opencode zen outage (dev) | Low | Fallback to NIM |

---

## 14. Testing Strategy

### 14.1 Unit Tests
- Per-agent logic
- Model registry lookup
- Fallback chain logic
- Safety filter accuracy
- Rate limit counter

### 14.2 Integration Tests
- Board → Department delegation
- CLO VETO blocks deployment
- CFO budget tracking
- Cache hit/miss behavior
- Code sandbox isolation

### 14.3 Stress Tests
- 24h sustained load (Phase 1: 16 agents)
- Rate limit boundary (inject overflow)
- Cache stampede (simultaneous miss)
- VETO cascade (multiple VETO votes)

### 14.4 Red Team Tests
- Jailbreak attempts (100 prompts)
- PII extraction (50 patterns)
- Code injection (SQLi, XSS, command)
- Prompt injection (indirect)
- Toxic output generation

---

## 15. Success Metrics

### 15.1 Per Phase
| Phase | Metric | Target |
|---|---|---|
| 1 | Agents operational | 16/16 |
| 1 | Safety accuracy | 95%+ red team caught |
| 1 | Daily cost | $0 |
| 2 | Code quality (reviewer catches) | 90%+ vulns caught |
| 2 | Sandbox isolation | 100% (no escapes) |
| 3 | Image/video generation success | 80%+ valid outputs |
| 3 | 50-agent stress (24h) | No rate limit breach |

### 15.2 Production Targets
- Uptime: 99% (allows for rate limit downtime)
- p95 latency: < 2s for non-vision tasks
- p95 latency: < 5s for vision/video tasks
- Cache hit rate: > 40%
- Cost: $0/month sustained

---

## 16. Dependencies

- Python 3.11+ (uv-managed)
- Redis server on :27123 (existing in vault)
- Docker (for code sandbox)
- GitHub repo: `MohamedNamper333/swarm-agent` (PAT configured)
- NVIDIA NIM API key (in vault, NOT to be committed)
- opencode zen config (dev only)

---

## 17. Change Log

| Date | Change | Author |
|---|---|---|
| 2026-08-10 | Initial roadmap v4 | Architecture team |
| TBD | Phase 1 completion | TBD |
| TBD | Phase 2 completion | TBD |
| TBD | Phase 3 completion (v4 done) | TBD |

---

## 18. Appendix: Decisions Log

| Decision | Choice | Reason |
|---|---|---|
| Hybrid safety | Inline + on-demand | Balance latency vs coverage |
| Cache: Redis | :27123 | Already provisioned |
| Phasing: 3 phases | 16→29→50 | Risk mitigation |
| Voice dept | DELETED | No chat model on NIM |
| opencode zen | Dev only | Reliability for prod |
| Frontend models | Only as VETO | Preserve quota |
| Circuit breaker | 80% daily limit | Buffer for critical ops |
| Code sandbox | Docker | Isolation guarantee |
