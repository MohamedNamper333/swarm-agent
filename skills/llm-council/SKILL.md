---
name: llm-council
description: |
  Use when the user wants to query multiple LLMs simultaneously through OpenRouter
  and get a "council" response where models review each other's answers.
  Also use when the user mentions "llm council", "karpathy/council",
  "multi-LLM", "compare LLM responses", "مجلس", "مقارنة نماذج".
  The project is at ~/.config/opencode/skills/llm-council/.
---

# LLM Council Skill

3-stage deliberation: query 8 models in parallel, rank via Chairman, synthesize final answer.

## 166 Skills Across 10 Council Categories

| # | Category | Council Model | Key Skills |
|---|----------|--------------|------------|
| 1 | **متكامل (General)** | Owl Alpha | fullstack-guardian, brainstorming, handoff, subagent-driven-development, coauthoring-docs, dispatching-parallel-agents, using-agent-skills |
| 2 | **استراتيجي (Strategic)** | Nemotron Ultra | architecture-designer, feature-forge, spec-miner, legacy-modernizer, saas-idea-finder, grill-me, writing-plans, executing-plans |
| 3 | **ناقد (Review)** | GPT-OSS-120b | code-review-and-quality, code-reviewer, security-reviewer, secure-code-guardian, the-fool, code-simplification, debugging-wizard, systematic-debugging, doubt-driven-development |
| 4 | **تقني (Technical)** | Nemotron Super | test-master, devops-engineer, playwright-expert, prompt-engineer, mcp-developer, building-mcp-servers, processing-pdf, testing-webapps, ci-cd-and-automation, git-workflow-and-versioning, context-engineering, source-driven-development |
| 5 | **مستشرف مستقبلي (Foresight)** | Hermes 405B | chaos-engineer, deep-research, grill-me, doubt-driven-development, the-fool, saas-idea-finder, interview-me, analysis-systems |
| 6 | **معماري (Architect)** | Qwen3 Coder | microservices-architect, cloud-architect, api-designer, api-and-interface-design, graphql-architect, rag-architect, database-optimizer, postgres-pro, terraform-engineer, kubernetes-specialist, architecture-designer, code-design-patterns |
| 7 | **مصمم إبداعي (Creative)** | Llama 3.3 70B | designing-frontend-interfaces, building-web-artifacts, applying-themes, creating-algorithmic-art, designing-canvas-art, artifact-variations, web-create-assets, web-asset-generator, frontend-ui-engineering |
| 8 | **مصمم بصري (Visual)** | Qwen3 Next | creating-slack-gifs, video-deep-understanding, video-use, manim-video, socialmedia-optimization, capture-dashboard, youtube-caption, youtube-search |
| 9 | **محلل بيانات (Data)** | Nemotron Nano | pandas-pro, spark-engineer, sql-pro, database-optimizer, postgres-pro, monitoring-expert, fine-tuning-expert, ml-pipeline, rag-architect, thematic-analysis, analysis-data-driven |
| 10 | **باحث مباشر (Research)** | Nous Hermes | deep-research, web-data-acquisition, web-crawling, webfetch-skill, amazon-uk-scraper, scraping-reddit, scraping-twitter, context7-search, context7-docs, youtube-search |

## 3-Stage Deliberation Flow

1. **Stage 1**: Query all 8 models in parallel (60s timeout each)
2. **Stage 2**: Chairman (Owl Alpha) ranks anonymized responses
3. **Stage 3**: Chairman synthesizes final answer from all responses + ranking

## Quick Start

```bash
cd ~/.config/opencode/skills/llm-council
source .venv/bin/activate
python -m backend.main
```

Then use `/council` command in opencode.

## API

- `POST /api/conversations` — create conversation
- `POST /api/conversations/{id}/message` — send query (returns stage1, stage2, stage3)
- `GET /api/conversations` — list all

## Config

Edit `~/.config/opencode/skills/llm-council/backend/config.py` to change models or timeout.
