---
description: Run the LLM Council with ALL installed skills as expert context. Queries 8 free models in parallel across 10 expert categories, ranks them via Chairman, and synthesizes a final answer.
---

# LLM Council Command

Run the full 3-stage llm-council using ALL installed skills as enriched context.

## Execution Steps

### Step 1: Start Backend
If port 8001 isn't responding, start the server:
```bash
if ! curl -sf http://localhost:8001/ > /dev/null 2>&1; then
  cd ~/.config/opencode/skills/llm-council && source .venv/bin/activate && nohup python -m backend.main > /tmp/llm-council.log 2>&1 &
  sleep 3
fi
```

### Step 2: Gather Skill Categories
The council has 10 expert categories. For each category, note the available specialties and append them as context:

```
Council has 166 skills across 10 categories:
1. General: fullstack-guardian, brainstorming, handoff, subagent-driven-development
2. Strategic: architecture-designer, feature-forge, spec-miner, saas-idea-finder
3. Review: code-review-and-quality, security-reviewer, the-fool, debugging-wizard
4. Technical: test-master, devops-engineer, playwright-expert, prompt-engineer
5. Foresight: chaos-engineer, deep-research, grill-me, doubt-driven-development
6. Architect: microservices-architect, cloud-architect, api-designer, rag-architect
7. Creative Design: designing-frontend-interfaces, artifact-variations, applying-themes
8. Visual Design: video-deep-understanding, manim-video, socialmedia-optimization
9. Data Analyst: pandas-pro, spark-engineer, sql-pro, monitoring-expert
10. Web Researcher: deep-research, web-crawling, webfetch-skill, scraping-reddit
```

### Step 3: Enrich & Send
```bash
cd ~/.config/opencode/skills/llm-council
source .venv/bin/activate
export $(grep -v '^#' .env | xargs)

CONV_ID=$(curl -sf -X POST http://localhost:8001/api/conversations \
  -H "Content-Type: application/json" \
  -d '{"title": "Council query"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

curl -sf -X POST "http://localhost:8001/api/conversations/$CONV_ID/message" \
  -H "Content-Type: application/json" \
  -d "{\"content\": \"[Context: 166 skills across 10 categories - General, Strategic, Review, Technical, Foresight, Architect, Creative, Visual, Data, Research]\\\\n\\\\n$ARGUMENTS\"}"
```

### Step 4: Present Results
Display the 3 stages to the user:
1. **Stage 1** — Each model's individual response
2. **Stage 2** — Rankings with aggregate scores
3. **Stage 3** — Chairman's synthesized final answer (emphasize this)
