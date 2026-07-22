---
name: swarm-agent
description: "Use the Swarm Agent — a collaborative team of 9 workers (1 coordinator + 8 specialists) + 2 dedicated vision agents, with 1082 specialised skills (plus 92 plugin skills on-demand) distributed across them — to analyse, design, build, review, debug, or visually inspect any type of project."
compatibility: opencode
---

# Swarm Agent — 9 Workers + 2 Vision Agents, 1082 Skills, One Team

> 📊 **التقييم الشامل**: [SWARM-EVALUATION.md](SWARM-EVALUATION.md) — تحليل كامل: نقاط قوة، ضعف، مقارنة بموديل واحد، سكور كارد

## Overview

1082 core skills → 9 domains → 9 workers + 2 vision agents → 1 coordinated swarm.

Instead of one model trying to master everything, each worker masters a domain with 30-100 skills, and all 9 work in parallel. The Coordinator orchestrates, distributes, and synthesises. The vision agents (MiMo V2.5, MiniMax M3) handle image/video/audio tasks on demand.

> 🎯 **Multimodal Workers**: The Explorer (MiMo V2.5) and MiniMax M3 can natively see images, understand video, and process audio — making them the swarm's eyes and ears. MiniMax M3 also excels at coding tasks.

## The 9 Workers & Their Full Skill Assignments

---

### 🧠 Coordinator — Big Pickle
**Model:** `opencode/big-pickle`
**Domain:** Architecture, Planning, Strategy, Decision-Making
**~65 skills**

Architecture & Design:
- `architect`, `architecture-designer`, `api-and-interface-design`, `api-designer`
- `code-design-patterns`, `microservices-architect`, `graphql-architect`
- `tradeoff-analysis`, `spec-driven-development`, `spec-miner`, `source-driven-development`

Planning & Strategy:
- `planning-and-task-breakdown`, `writing-plans`, `executing-plans`
- `subagent-driven-development`, `incremental-implementation`, `project-bootstrap`
- `brainstorming`, `idea-refine`, `feature-forge`
- `interview-me`, `the-fool`, `council-thinking`, `doubt-driven-development`

Thinking & Decision:
- `first-principles-thinking`, `thinking-first-principles`
- `thinking-decision`, `thinking-lateral`, `thinking-metacognition`
- `decision-log`

Deep Knowledge:
- `physics`, `mathematics`, `logic`, `philosophy`
- `astropy`, `qiskit`

Startup & Strategy:
- `startup-strategist`, `strategic-compact`, `product-lens`, `what-if-oracle`

Thinking:
- `scientific-critical-thinking`, `scientific-brainstorming`, `consciousness-council`
- `failure-navigator`, `mpp-evaluator`

Founder Strategy:
- `problem-validator`, `customer-hypothesis`, `competitor-mapper`, `assumption-mapper`
- `mvp-scoper`, `user-interview-guide`

Zero→Company Pipeline:
- `zero-to-company`

Vision & Product:
- `product-manager`, `project-idea-validator`, `business-analyst`
- `competitive-analyst`, `assumption-mapping`, `market-researcher`
- `research-analyst`, `trend-analyst`, `risk-manager`
- `customer-success-manager`

Orchestration:
- `multi-agent-coordinator`, `workflow-orchestrator`, `task-distributor`
- `knowledge-synthesizer`, `context-manager`, `golden-path-designer`
- `architect-reviewer`, `codebase-orchestrator`, `platform-product-manager`
- `policy-guardrail-designer`, `eval-engineer`
- `agent-organizer`, `agent-installer`

Systems:
- `analysis-systems`

LLM:
- `llm-council`

Meta & Context:
- `context-engineering`, `using-agent-skills`, `dispatching-parallel-agents`
- `documentation-and-adrs`, `legacy-modernizer`

---

### 💡 Innovator — DeepSeek V4 Flash Free
**Model:** `opencode/deepseek-v4-flash-free`
**Domain:** All Languages, Frameworks, Frontend & Backend
**~110 skills**

React Ecosystem:
- `react-expert`, `react-native-expert`, `nextjs-developer`
- `vue-expert`, `vue-expert-js`, `angular-architect`
- `svelte`, `astro`, `remix`, `solid`, `qwik`

CSS & Styling:
- `tailwind-css`, `css-in-js`

State Management:
- `zustand`, `tanstack-query`, `pinia`

Desktop & Mobile:
- `electron`, `tauri`, `expo`

Animation & 3D:
- `framer-motion`, `animejs-animation`, `magic-animator`
- `review-animations`, `fixing-motion-performance`
- `makepad-animation`, `makepad-shaders`
- `threejs-fundamentals`, `threejs-geometry`, `threejs-materials`
- `threejs-lighting`, `threejs-textures`, `threejs-loaders`
- `threejs-interaction`, `threejs-animation`, `threejs-shaders`
- `threejs-postprocessing`
- `spline-3d-integration`, `3d-ui`, `3d-web-experience`
- `premium-3d-website`, `isometric-design`
- `spatial-design`, `spatial-computing-ui`, `holographic-ui`

Design Systems & UI Patterns:
- `radix-ui-design-system`, `tailwind-design-system`
- `ui-tokens`, `ui-component`, `ui-pattern`
- `bento-ui`, `floating-ui`, `aurora-ui`
- `command-center-ui`, `dashboard-design`, `data-dense-design`
- `canvas-design`, `shader-programming-glsl`

Visual Styles:
- `gradient-design`, `duotone-design`, `color-blocking`
- `typography-first`, `cyberpunk-ui`, `retro-design`
- `swiss-design`, `material-design`

UX & Brand:
- `ui-visual-validator`, `ux-audit`, `ux-flow`
- `brand-guidelines`

Interface Design:
- `interface-design`, `uxui-principles`, `ui-ux-designer`
- `ui-ux-pro-max`, `design-spells`, `design-md`
- `design-orchestration`, `stitch-ui-design`
- `magic-ui-generator`, `deterministic-design`
- `kpi-dashboard-design`

UX Research & Accessibility:
- `ux-designer-skill`, `ux-feedback`, `ux-copy`
- `ui-a11y`, `ui-review`, `wcag-audit-patterns`
- `accessibility-compliance-accessibility-audit`
- `ux-persuasion-engineer`, `product-design`
- `mobile-design`, `accesslint-audit`

Visual Design & Art:
- `canvas-design`, `algorithmic-art`, `imagen`
- `image-studio`, `image-generator`, `remotion`
- `remotion-best-practices`, `article-illustrations`
- `visual-emotion-engineer`, `ad-creative`
- `canva-automation`, `game-art`, `fal-image-edit`
- `ai-studio-image`, `seo-image-gen`, `seo-images`
- `comfyui-gateway`

Frontend/Artifacts:
- `web-artifacts-builder`, `react-ui-patterns`
- `frontend-ui-dark-ts`, `senior-frontend`
- `browser-extension-builder`, `tailwind-patterns`
- `react-patterns`, `nextjs-best-practices`, `sveltekit`
- `frontend-dev-guidelines`, `shadcn`
- `vercel-react-view-transitions`

Taste & Premium Design:
- `taste-skill`, `taste-skill-v1`, `gpt-tasteskill`
- `brandkit`, `brutalist-skill`, `soft-skill`
- `minimalist-skill`, `redesign-skill`, `stitch-skill`
- `output-skill`, `imagegen-frontend-web`, `imagegen-frontend-mobile`
- `image-to-code-skill`, `gpt-taste`
- `stitch-design-taste`, `design-taste-frontend`
- `high-end-visual-design`, `emil-design-eng`
- `redesign-existing-projects`, `industrial-brutalist-ui`
- `minimalist-ui`, `ckw-design`

Caveman Workflow:
- `caveman-caveman`, `caveman-caveman-commit`
- `caveman-caveman-compress`, `caveman-caveman-help`
- `caveman-caveman-review`, `caveman-caveman-stats`
- `caveman-cavecrew`

Prompts & Templates:
- `fable5-websites-prompt` — Fable 5 creative website builder prompt
- `prompt-engineering`, `prompt-engineering-patterns`
- `prompt-caching`, `prompt-library`, `enhance-prompt`
- `llm-prompt-optimizer`, `llm-application-dev-prompt-optimize`
- `templates`, `documentation-templates`
- `fastapi-templates`, `github-actions-templates`
- `incident-runbook-templates`, `notion-template-business`
- `obsidian-clipper-template-creator`, `odoo-qweb-templates`
- `defi-protocol-templates`, `employment-contract-templates`

Agent Frameworks & Orchestration:
- `ecc` — cross-harness agent OS (ECC framework)
- `gstack` — Garry Tan's software factory (YC CEO): 23 specialists + 8 power tools
- `gstack-autoplan`, `gstack-benchmark`, `gstack-benchmark-models`
- `gstack-browse`, `gstack-canary`, `gstack-careful`, `gstack-codex`
- `gstack-connect-chrome`, `gstack-context-restore`, `gstack-context-save`
- `gstack-cso`, `gstack-design-consultation`, `gstack-design-html`
- `gstack-design-review`, `gstack-design-shotgun`, `gstack-devex-review`
- `gstack-diagram`, `gstack-document-generate`, `gstack-document-release`
- `gstack-freeze`, `gstack-gstack-upgrade`, `gstack-guard`, `gstack-health`
- `gstack-investigate`, `gstack-ios-clean`, `gstack-ios-design-review`
- `gstack-ios-fix`, `gstack-ios-qa`, `gstack-ios-sync`
- `gstack-land-and-deploy`, `gstack-landing-report`, `gstack-learn`
- `gstack-make-pdf`, `gstack-office-hours`, `gstack-open-gstack-browser`
- `gstack-pair-agent`, `gstack-plan-ceo-review`, `gstack-plan-design-review`
- `gstack-plan-devex-review`, `gstack-plan-eng-review`, `gstack-plan-tune`
- `gstack-qa`, `gstack-qa-only`, `gstack-retro`, `gstack-review`, `gstack-scrape`
- `gstack-setup-browser-cookies`, `gstack-setup-deploy`, `gstack-setup-gbrain`
- `gstack-ship`, `gstack-skillify`, `gstack-spec`, `gstack-sync-gbrain`
- `gstack-unfreeze`
- `gstack-gstack-openclaw-ceo-review`, `gstack-gstack-openclaw-investigate`
- `gstack-gstack-openclaw-office-hours`, `gstack-gstack-openclaw-retro`
- `agentic-engineering` — designing agentic workflows
- `autonomous-agent-harness` — self-directing agent loops
- `autonomous-agents`, `autonomous-agent-patterns`
- `computer-use-agents`, `hosted-agents`, `hosted-agents-v2-py`
- `voice-agents`, `pipecat-friday-agent`
- `ai-agent-development`, `ai-agents-architect`
- `agent-squad`, `multi-agent-architect`
- `multi-agent-patterns`, `multi-agent-task-orchestrator`
- `multi-agent-brainstorming`, `parallel-agents`
- `subagent-orchestrator`, `subagent-driver`
- `agent-orchestrator`, `agent-orchestration-improve-agent`
- `agent-orchestration-multi-agent-optimize`
- `orchestrate-batch-refactor`, `saga-orchestration`
- `tdd-orchestrator`, `tdd-workflows`, `tdd-workflows-tdd-cycle`
- `tdd-workflows-tdd-green`, `tdd-workflows-tdd-red`, `tdd-workflows-tdd-refactor`
- `workflow-automation`, `workflow-orchestration-patterns`
- `workflow-patterns`, `open-dynamic-workflows`
- `n8n-workflow-patterns`, `cicd-automation-workflow-automate`
- `gitops-workflow`, `expo-cicd-workflows`
- `github-workflow-automation`, `git-advanced-workflows`
- `git-pr-workflows-git-workflow`, `git-pr-workflows-onboard`
- `git-pr-workflows-pr-enhance`
- `agent-framework-azure-ai-py`, `azure-ai-agents-persistent-dotnet`
- `azure-ai-agents-persistent-java`
- `m365-agents-dotnet`, `m365-agents-py`, `m365-agents-ts`
- `llm-application-dev-langchain-agent`
- `agent-creator`, `agent-tool-builder`, `agent-manager-skill`
- `agent-memory-systems`, `agent-memory-mcp`, `hierarchical-agent-memory`
- `agent-evaluation`, `agent-evaluator`
- `agentic-actions-auditor`, `agenttrace-session-audit`
- `agents-md`, `agents-v2-py`
- `agentflow`, `agentfolio`, `agentmail`, `agentphone`
- `global-chat-agent-discovery`
- `crypto-bd-agent`, `ios-debugger-agent`, `lambdatest-agent-skills`
- `antigravity-agent-manager`, `antigravity-skill-orchestrator`
- `antigravity-workflows`, `acceptance-orchestrator`
- `context-agent`, `ecl-harness-engineer`
- `ejentum-reasoning-harness`
- `full-stack-orchestration-full-stack-feature`
- `fal-workflow`, `ax-extract-workflow`
- `ml-pipeline-workflow`
- `codex-fable5`, `codex-review`
- `error-debugging-multi-agent-review`
- `performance-testing-review-multi-agent-review`
- `continuous-agent-loop`, `continuous-learning`, `continuous-learning-v2`
- `llm-trading-agent-security`
- `team-agent-orchestration`

Ads & Marketing:
- `ads-meta`, `ads-google`, `ads-tiktok`, `ads-x`, `ads-youtube`
- `ads-linkedin`, `ads-pinterest`, `ads-reddit`, `ads-snapchat`
- `ads-amazon`, `ads-apple`, `ads-microsoft`
- `ads-audit`, `ads-plan`, `ads-budget`, `ads-create`
- `ads-creative`, `ads-generate`, `ads-photoshoot`
- `ads-launch`, `ads-landing`, `ads-optimize`, `ads-monitor`
- `ads-report`, `ads-research`, `ads-test`, `ads-validate`
- `ads-attribution`, `ads-competitor`, `ads-dna`
- `ads-math`, `ads-server-side-tracking`, `ads-setup`
- `brand-guidelines`, `brand-guidelines-anthropic`, `brand-guidelines-community`
- `brand-perception-psychologist`, `social-content`, `social-orchestrator`
- `social-post-writer-seo`, `social-proof-architect`, `socialclaw`
- `social-metadata-hardening`
- `seo`, `seo-audit`, `seo-fundamentals`, `seo-technical`
- `seo-content`, `seo-content-writer`, `seo-plan`, `seo-page`
- `seo-schema`, `seo-sitemap`, `ai-seo`, `programmatic-seo`
- `seo-aeo-blog-writer`, `seo-aeo-content-cluster`, `seo-keyword-strategist`
- `seo-competitor-pages`, `seo-cannibalization-detector`
- `seo-content-auditor`, `seo-content-planner`, `seo-content-refresher`
- `seo-meta-optimizer`, `seo-snippet-hunter`, `seo-structure-architect`
- `seo-hreflang`, `seo-geo`, `seo-dataforseo`, `seo-forensic-incident-response`
- `seo-authority-builder`, `tools-page-seo-optimizer`
- `local-legal-seo-audit`, `nextjs-seo-indexing`
- `youtube-seo-optimizer`, `wordpress-centric-high-seo-optimized-blogwriting-skill`
- `seo-aeo-landing-page-writer`, `seo-aeo-meta-description-generator`
- `seo-aeo-schema-generator`, `seo-aeo-internal-linking`
- `seo-aeo-content-quality-auditor`, `seo-aeo-keyword-research`
- `market-sizing-analysis`, `startup-business-analyst-market-opportunity`
- `apify-market-research`, `apify-lead-generation`
- `apify-brand-reputation-monitoring`, `apify-content-analytics`
- `apify-influencer-discovery`
- `growth-engine`, `analytics-product`, `analytics-tracking`
- `google-analytics-automation`, `product-marketing-context`
- `cold-email`, `email-sequence`, `email-systems`
- `lead-magnets`, `landing-page-generator`, `sales-automator`
- `sales-enablement`, `salesforce-automation`, `salesforce-development`
- `marketing-ideas`, `marketing-psychology`, `copywriting`
- `copy-editing`, `copywriting-psychologist`
- `activecampaign-automation`, `mailtrap-sending-emails`
- `odoo-sales-crm-expert`
- `xiaohongshu-content-strategist`, `influencer-discovery`

AI SDKs:
- `openai-sdk`

Build Tools:
- `vite`

Databases:
- `prisma`

Scientific Computing:
- `scientific-computing`, `sympy`

Backend Frameworks:
- `nestjs-expert`, `fastapi-expert`, `django-expert`
- `laravel-specialist`, `rails-expert`, `php-pro`
- `spring-boot-engineer`, `java-architect`
- `csharp-developer`, `dotnet-core-expert`

Systems Languages:
- `golang-pro`, `rust-engineer`, `cpp-pro`
- `swift-expert`, `kotlin-specialist`

Core Languages:
- `typescript-pro`, `javascript-pro`, `python-pro`
- `fullstack-guardian`, `developer`

Mobile:
- `flutter-expert`

Tools:
- `mcp-developer`
- `cli-developer`, `websocket-engineer`
- `mcp-server-patterns`, `autonomous-agent-harness`

Data Tools:
- `dask`, `polars`, `networkx`

Backend Patterns:
- `backend-patterns`, `api-design`

Frontend Patterns:
- `frontend-patterns`

Code Quality:
- `coding-standards`, `blueprint`

Architecture:
- `architecture-decision-records`
- `architecture-explainer`

Founder Build:
- `stack-selector`, `integration-picker`, `feature-sequencer`

General Dev:
- `backend-developer`, `frontend-developer`, `fullstack-developer`
- `ai-engineer`, `llm-architect`
- `node-specialist`, `react-specialist`
- `fastapi-developer`, `django-developer`, `symfony-specialist`
- `wordpress-master`, `dotnet-framework-4.8-expert`
- `electron-pro`, `expo-react-native-expert`
- `elm`, `elixir-expert`, `erlang-expert`
- `blockchain-developer`, `iot-engineer`, `network-engineer`
- `fintech-engineer`, `search-specialist`, `quant-analyst`

Vercel Ecosystem:
- `web-design-guidelines`, `writing-guidelines`
- `deploy-to-vercel`, `vercel-cli-with-tokens`
- `vercel-optimize`, `vercel-react-best-practices`
- `vercel-composition-patterns`, `vercel-react-view-transitions`
- `vercel-react-native-skills`

Data & ML:
- `data-scientist`, `data-engineer`, `data-analyst`, `database-administrator`
- `machine-learning-engineer`, `ml-engineer`, `mlops-engineer`
- `nlp-engineer`, `reinforcement-learning-engineer`

Dev Tools:
- `build-engineer`, `tooling-engineer`, `deployment-engineer`
- `dependency-manager`, `dx-optimizer`, `docker-expert`
- `terragrunt-expert`, `azure-infra-engineer`, `backstage-specialist`
- `code-mapper`, `refactoring-specialist`

Documentation:
- `readme-generator`, `api-documenter`, `documentation-engineer`
- `technical-writer`

Windows Ecosystem:
- `powershell-5.1-expert`, `powershell-7-expert`, `powershell-module-architect`
- `powershell-security-hardening`, `powershell-ui-architect`

---

### 🔍 Critic — Nemotron 3 Nano 30B
**Model:** `ollama-cloud/nemotron-3-nano:30b`
**Domain:** Code Quality, Security, Testing, Debugging
**~45 skills**

Code Review:
- `code-reviewer`, `code-review-and-quality`, `code-simplification`
- `clean-code-guard`, `receiving-code-review`, `requesting-code-review`

Security:
- `secure-code-guardian`, `security-reviewer`, `security-and-hardening`

Testing:
- `test-driven-development`, `test-master`
- `playwright-expert`, `browser-testing-with-devtools`
- `vitest`, `qa-architect`, `tdd-workflow`, `e2e-testing`

Security:
- `security-review`

Debugging:
- `debugging-wizard`, `debugging-and-error-recovery`

Quality:
- `performance-optimization`

Auth Security:
- `clerk`, `next-auth`

Testing & QA:
- `qa-expert`, `test-automator`, `debugger`
- `error-detective`, `error-coordinator`, `hallucination-investigator`
- `prompt-regression-tester`, `responsible-ai-reviewer`
- `reviewer`
- `browser-debugger`, `incident-responder`

AI Governance & Compliance:
- `ai-governance-auditor`, `ad-security-reviewer`
- `model-risk-manager`, `compliance-auditor`
- `hipaa-compliance`, `gdpr-ccpa-compliance`
- `penetration-tester`, `security-auditor`, `security-engineer`

---

### 🏗️ Architect — Nemotron 3 Ultra Free
**Model:** `opencode/nemotron-3-ultra-free`
**Domain:** Infrastructure, DevOps, Data, Systems
**~51 skills**

Cloud & DevOps:
- `cloud-architect`, `devops-engineer`
- `kubernetes-specialist`, `terraform-engineer`
- `ci-cd-and-automation`

BaaS:
- `supabase`

CI/CD & Containers:
- `github-actions`, `docker-compose`, `dev-containers`

Serverless & Deploy:
- `serverless`, `vercel-deploy`

Caching & Infrastructure:
- `redis`

Monitoring & Reliability:
- `monitoring-expert`, `observability-and-instrumentation`
- `sre-engineer`, `chaos-engineer`

Databases:
- `database-optimizer`, `postgres-pro`, `sql-pro`
- `spark-engineer`, `pandas-pro`

Statistics & Science:
- `statistics-probability`, `chemistry`
- `statsmodels`, `pymc`

ML & Data Science:
- `scikit-learn`, `pymatgen`

Statistics & Analysis:
- `statistical-analysis`, `exploratory-data-analysis`, `experimental-design`

Cheminformatics:
- `rdkit`

Data & ML Infrastructure:
- `ml-pipeline`, `rag-architect`
- `analysis-data-driven`

Search:
- `algolia`, `meilisearch`, `elasticsearch`

Infrastructure:
- `embedded-systems`, `atlassian-mcp`
- `git-workflow-and-versioning`, `using-git-worktrees`

Monorepo:
- `turborepo`, `nx`

Specialised:
- `fine-tuning-expert`, `prompt-engineer`
- `deprecation-and-migration`, `shipping-and-launch`

---

### 🧭 Explorer — MiMo V2.5 Free
**Model:** `opencode/mimo-v2.5-free`
**Domain:** Research, Scraping, Content Discovery, **Vision & Multimodal**
**~55 skills**

> ⚡ **MiMo V2.5 is the only OMNIMODAL model in the swarm.** It natively sees images, understands videos (frame-by-frame), and processes audio — all in one call. No adapters, no preprocessing. Use this worker whenever the task involves visual or audio analysis.

Deep Research:
- `business-analysis`, `polymath`
- `paper-lookup`, `hypothesis-generation`
- `literature-review`, `market-research-reports`, `research-grants`

Scientific Methods:
- `scientific-writing`, `experimental-design`, `research-ops`

Vision & Multimodal (Native):
- — analyze videos, extract transcripts + visual evidence
- — capture & analyze browser screenshots
- `visual-asset-generator` — generate images via external APIs
- — create animated GIFs from video/images
- `accessibility-tester` — visual accessibility audit
- `ui-ux-tester` — visual UI testing
- `design-bridge` — translate design specs into UI

Scientific & Docs Research:
- `d3-charts`

Scientific & Docs Research:
- `scientific-literature-researcher`, `docs-researcher`, `data-researcher`

Marketing & Sales:
- `content-marketer`, `seo-specialist`, `sales-engineer`
- `growth-loops`, `content-quality-editor`
- `ab-test-analysis`, `cohort-analysis`

AI Ops & Writing:
- `ai-observability-engineer`, `ai-writing-auditor`

General Ops:
- `legal-advisor`, `license-engineer`, `healthcare-admin`
- `it-ops-orchestrator`, `windows-infra-admin`, `m365-admin`
- `idp-architect`, `platform-engineer`
- `slack-expert`, `payment-integration`
- `scrum-master`

---

### ✅ Reviewer — Nemotron 3 Super
**Model:** `ollama-cloud/nemotron-3-super`
**Domain:** UX, Design, Project Management, Specialised Domains
**~110 skills**

Frontend & Design:
- `frontend-ui-engineering`

Visual & Spatial Design:
- `graphic-design`, `ui-design`, `ux-design`
- `industrial-design`, `architecture-design`, `motion-graphics`

Data Visualization:
- `matplotlib`, `scientific-visualization`, `seaborn`, `infographics`

UI Component Libraries:
- `storybook`, `shadcn-ui`, `figma-integration`, `frontend-design`

UX Research:
- `ux-research`

Product & Startup:
- `prd-architect`, `product-designer`, `product-capability`
- `backlog-manager`, `startup-strategist`
- `growth-consultant`, `content-strategist`

Business Development:
- `investor-materials`, `investor-outreach`, `sales-deck-specialist`
- `market-research`, `strategic-compact`

Founder Design:
- `design-direction-setter`, `ux-flow-designer`, `ux-heuristics-reviewer`

Founder Launch:
- `pricing-model-framer`, `positioning-writer`, `launch-plan-builder`, `landing-page-copywriter`

Founder PMF & Growth:
- `retention-loop-designer`, `pmf-signal-reader`, `north-star-definer`
- `growth-loop-builder`, `churn-diagnostician`

Founder Scale:
- `first-hire-brief`, `founder-partner`, `build-cycle`

Design & Frontend:
- `design-system`, `frontend-slides`

Project Management:
- `pm-agile`, `pm-budget`, `pm-change`, `pm-communication`
- `pm-large-scale`, `pm-meetings`, `pm-resource`
- `pm-risk`, `pm-stakeholder`, `pm-team-leadership`
- `project-flow-ops`, `team-builder`

Payments & Communications:
- `stripe`, `paypal`, `twilio`, `sendgrid`

Analytics & Monitoring:
- `sentry`, `posthog`

Accessibility & Internationalisation:
- `a11y`, `i18next`

Specialised Domains:
- `game-developer`, `shopify-expert`
- `wordpress-pro`, `salesforce-developer`
- `finishing-a-development-branch`

Zero→Company:
- `zero-to-company`

---

### 🚀 Vision-Coder — MiniMax M3
**Model:** `ollama-cloud/minimax-m3`
**Domain:** Vision + Coding + Agentic Tasks (multimodal, 1M context)

MiniMax M3 is the swarm's super-worker: native image/video/audio input + frontier coding + 1M token context. Use it when you need both visual understanding AND code generation.

Vision & Multimodal:
- `visual-asset-generator`

Full Code Access:
- All coding, infrastructure, and analysis skills

Dedicated agent: `opencode --model vision-max "<prompt>"`

---

### 🧩 Reasoner — Tencent Hy3 Free
**Model:** `opencode/hy3-free`
**Domain:** Reasoning, Logic, Agentic Planning, Multi-step Problem Solving

> ⚡ **Hy3 is the swarm's deep thinker.** A 295B MoE model (21B active) optimized for complex reasoning, chain-of-thought, and multi-step planning. Use this worker when the task requires deep logic, mathematical reasoning, or multi-step problem decomposition. **80 skills across 4 domains.**

**Reasoning (20 skills — deep thinking, mental models, evidence-based + cross-domain analysis):**
- `critical-thinking-logical-reasoning` — structured logical reasoning chains (sammcj)
- `thought-based-reasoning` — deep multi-perspective reasoning (neolabhq)
- `systems-thinking` — seeing systems, feedback loops, emergence (refoundai)
- `sequential-thinking` — step-by-step reasoning chains (mrgoonie)
- `thinking-systems` — systematic thinking methodology (tjboudreaux)
- `systems-thinking-leverage` — finding leverage points in complex systems (lyndonkl)
- `thinking-partner` — Socratic dialogue reasoning (mattnowdev)
- `first-principles` — first principles decomposition (guia-matthieu)
- `math-reasoning` — mathematical and formal reasoning (lingzhi227)
- `scientific-critical-thinking` — evidence-based reasoning and hypothesis testing
- `analysis-data-driven` — data-driven analysis and evidence-based reasoning
- `analysis-systems` — systems-level analysis and emergent behavior reasoning
- `calculus-analysis` — calculus and mathematical analysis reasoning
- `linear-algebra-geometry` — linear algebra, geometry, and spatial reasoning
- `statistics-probability` — statistical and probabilistic reasoning frameworks
- `mathematics` — comprehensive mathematical problem-solving reasoning
- `scientific-brainstorming` — creative scientific reasoning and exploration
- `polymath` — cross-domain knowledge synthesis and reasoning
- `research-analyst` — structured research investigation and analysis
- `quant-analyst` — quantitative reasoning and numerical analysis

**Logic (20 skills — formal logic, fallacies, cognitive patterns, verification + frameworks):**
- `firebase-ai-logic` — formal logic rules and reasoning (firebase 34K)
- `firebase-ai-logic-basics` — logic foundations (firebase 65K)
- `cognitive-biases` — identify logical fallacies and cognitive biases (guia-matthieu)
- `cognitive-walkthrough` — step-by-step cognitive analysis (mastepanoski)
- `cognitive-pattern` — pattern recognition in logic (ruvnet)
- `formal-logic` — propositional and predicate logic
- `logic` — logical reasoning framework
- `critical-thinking` — evaluate arguments and claims
- `first-principles-thinking` — break down to fundamentals
- `thinking-first-principles` — reasoning from basics up
- `anti-sycophancy` — logical consistency and independent verification
- `validate-implementation-plan` — plan logic and reasoning validation
- `experimental-design` — experiment design logic and methodology
- `ab-test-analysis` — A/B testing logic and statistical inference
- `cohort-analysis` — behavioral cohort logic and pattern analysis
- `attack-tree-construction` — logical threat tree construction and analysis
- `stride-analysis-patterns` — STRIDE logical threat modeling framework
- `decision-log` — decision logic recording and rationale tracking
- `business-analysis` — structured business logic and framework analysis
- `hypothesis-generation` — structured hypothesis formulation and logic

**Agentic Planning (20 skills — multi-step workflows, task decomposition, orchestration + PM):**
- `planning-with-files` — structured planning with file-based tracking (othmanadi 36K)
- `agentic-engineering` — designing agentic workflows (affaan-m)
- `writing-plans` — plan creation and documentation
- `executing-plans` — plan execution and tracking
- `planning-and-task-breakdown` — task decomposition and sequencing
- `context-engineering` — context management for complex workflows
- `workflow-orchestrator` — multi-step workflow coordination
- `task-distributor` — distributing subtasks across workers
- `multi-agent-coordinator` — coordinating multiple AI agents
- `agent-organizer` — organizing agent teams for complex tasks
- `project-manager` — project planning and milestone management
- `backlog-manager` — backlog planning and task management
- `backlog-grooming` — backlog refinement and prioritization
- `scrum-master` — Scrum process planning and facilitation
- `pm-agile` — Agile methodology and sprint planning
- `pm-resource` — resource planning and capacity management
- `pm-risk` — risk management planning and mitigation
- `project-bootstrap` — project initialization planning and setup
- `refine-task` — task refinement and readiness assessment
- `codebase-orchestrator` — repository-wide refactor governance and planning

**Multi-step Problem Solving (20 skills — debugging, RCA, decision processes + operations):**
- `systematic-debugging` — systematic debugging methodology (obra 180K)
- `root-cause-tracing` — trace root causes through complex systems (neolabhq)
- `root-cause-analysis` — structured root cause analysis (aj-geddes)
- `debugging-strategies` — multiple debugging strategies (wshobson 10K)
- `problem-solving` — general problem-solving framework (mrgoonie)
- `running-decision-processes` — decision-making processes (refoundai)
- `debugging-and-error-recovery` — error recovery and fixing
- `debugging-wizard` — advanced debugging techniques
- `diagnosing-root-causes` — root cause diagnosis
- `doubt-driven-development` — adversarial review and verification
- `incident-responder` — incident response problem solving and triage
- `failure-navigator` — navigating product and system failures
- `churn-diagnostician` — diagnosing churn root causes and patterns
- `hallucination-investigator` — investigating AI hallucination root causes
- `error-detective` — error detection and diagnosis
- `error-coordinator` — coordinating error resolution across systems
- `performance-engineer` — performance problem solving and optimization
- `performance-monitor` — performance monitoring and anomaly detection
- `debugger` — systematic debugging across code paths
- `risk-manager` — risk analysis and problem resolution

---

## Full Strategy Reference

### brainstorm (default)
Every worker receives the **same problem** with their unique perspective:
```
🧠 Coordinator (Big Pickle) → Architecture & planning angle
💡 innovator (DeepSeek V4 Flash Free) → Implementation & code angle
🔍 critic (Nemotron 3 Nano 30B) → Quality & security angle
🏗️ architect (Nemotron 3 Ultra Free) → Infrastructure & data angle
🧭 explorer (MiMo V2.5 Free) → Research & VISION (image/video/audio)
🚀 vision-coder (MiniMax M3) → VISION + coding + agentic tasks
✅ reviewer (Nemotron 3 Super) → UX & process angle
🧩 reasoner (Tencent Hy3 Free) → Reasoning & logic & multi-step planning
🎯 swarm-worker-qa (Nemotron 3 Ultra Free) → Build, run, verify, test
```

### divide-conquer
Problem is split into **9 parts**, one per worker's speciality.

### explore
Each worker **investigates from their domain** — security, infra, architecture, UX, vision, reasoning, etc.

### debate
Workers **argue from their domain perspective** — the architect proposes, the critic challenges, the innovator offers alternatives, the reasoner provides logical analysis.

### review
Focused **review from 9 angles** — each worker uses their domain's skills.

### stepwise-auto (auto-verified — no user interruption)
Each step auto-verifies across 5 dimensions and decides PASS/REDO/FORCE without asking the user:

#### Per-Step Pipeline
```
Step N:
 1. EXECUTE — 9 workers in parallel (each from their domain)
 2. REVIEW 1 (Quality & Gaps) — code-reviewer, security-reviewer, clean-code-guard
 3. REVIEW 2 (Philosophy & Design) — architect-reviewer, tradeoff-analysis, first-principles
 4. DOMAIN CHECK — dynamic skill selector based on step context
 5. TESTING — test-master, improving-test-suites
 6. AUTO-VERDICT — weighted score + redo logic
```

#### Scoring Rubric (each dimension scored 1-10)

| Dimension | Weight | Source Skills | What It Checks |
|-----------|--------|---------------|----------------|
| Code Quality | 25% | code-reviewer, clean-code-guard | logic, duplication, complexity, maintainability |
| Security & Gaps | 20% | security-reviewer, secure-code-guardian | injections, vulns, edge cases, error handling |
| Design Philosophy | 15% | architect-reviewer, tradeoff-analysis | why this approach, alternatives, trade-offs |
| Domain Correctness | 20% | Domain-specific (physics/design/data/…) | fits context, correct properties, appropriate patterns |
| Testing Intensity | 20% | test-master, improving-test-suites | coverage, edge cases, property-based tests |

**Domain Check dynamically selects:**
- **Physics/Engineering** → physics, scientific-critical-thinking
- **Design/UI** → design-system, ux-heuristics-reviewer, ui-designer
- **Code/Architecture** → architect-reviewer, code-review-checklist
- **Data/Database** → database-optimizer, sql-pro, pandas-pro
- **Security** → penetration-tester, security-auditor
- **Infrastructure** → cloud-architect, terraform-engineer, kubernetes-specialist
- **AI/ML** → ml-engineer, rag-architect, eval-engineer

#### Auto-Verdict Logic

```
weighted_score = (quality×25 + security×20 + philosophy×15 + domain×20 + testing×20) / 100

≥ 7.5/10 and no critical issues → PASS → next step
5.0–7.4/10 or minor issues → REDO → same approach + feedback
< 5.0/10 or critical issues → REDO → strict feedback
```

#### Auto-Verdict Calculation Implementation (Python3 PRIME + bc FALLBACK)

**PRIME Implementation (Python3 with decimal.Decimal):**

```python
#!/usr/bin/env python3
"""
Auto-Verdict PRIME Calculator
Calculates weighted score with decimal precision.
Usage: python3 auto_verdict.py quality security philosophy domain testing
"""
import sys
from decimal import Decimal, getcontext

getcontext().prec = 28

WEIGHTS = {
    "quality": Decimal("0.25"),
    "security": Decimal("0.20"),
    "philosophy": Decimal("0.15"),
    "domain": Decimal("0.20"),
    "testing": Decimal("0.20"),
}

THRESHOLDS = {
    "PASS": Decimal("7.5"),
    "REDO_MIN": Decimal("5.0"),
}

def calculate_verdict(scores: dict) -> dict:
    """Calculate weighted verdict with decimal precision."""
    weighted = Decimal("0")
    for dim, weight in WEIGHTS.items():
        weighted += Decimal(str(scores[dim])) * weight
    
    verdict = "FAIL"
    if weighted >= THRESHOLDS["PASS"]:
        verdict = "PASS"
    elif weighted >= THRESHOLDS["REDO_MIN"]:
        verdict = "REDO"
    else:
        verdict = "FORCE"
    
    return {
        "weighted_score": round(weighted, 4),
        "verdict": verdict,
        "breakdown": {k: float(v * Decimal(str(scores[k]))) for k, v in WEIGHTS.items()}
    }

if __name__ == "__main__":
    if len(sys.argv) != 6:
        print("Usage: python3 auto_verdict.py <quality> <security> <philosophy> <domain> <testing>")
        sys.exit(1)
    
    scores = {
        "quality": sys.argv[1],
        "security": sys.argv[2],
        "philosophy": sys.argv[3],
        "domain": sys.argv[4],
        "testing": sys.argv[5],
    }
    result = calculate_verdict(scores)
    print(f"Weighted Score: {result['weighted_score']}")
    print(f"Verdict: {result['verdict']}")
    print(f"Breakdown: {result['breakdown']}")
```

**FALLBACK Implementation (bc):**

```bash
#!/bin/bash
# Auto-Verdict FALLBACK Calculator using bc
# Usage: ./auto_verdict.sh quality security philosophy domain testing

quality=$1
security=$2
philosophy=$3
domain=$4
testing=$5

# Weighted score calculation with bc
weighted=$(echo "scale=4; ($quality*0.25)+($security*0.20)+($philosophy*0.15)+($domain*0.20)+($testing*0.20)" | bc -l)

# Determine verdict
if (( $(echo "$weighted >= 7.5" | bc -l) )); then
    verdict="PASS"
elif (( $(echo "$weighted >= 5.0" | bc -l) )); then
    verdict="REDO"
else
    verdict="FORCE"
fi

echo "Weighted Score: $weighted"
echo "Verdict: $verdict"
```

**Usage in Pipeline:**
```bash
# PRIME (preferred)
python3 auto_verdict.py 8 9 7 8 9

# FALLBACK (if python3 unavailable)
./auto_verdict.sh 8 9 7 8 9
```

#### Worker Output Format Requirement

**كل worker يجب أن يبدأ رده بـ:**
```
[WORKER: <subagent_type> | MODEL: <model_id>]
FINDING: <what was found>
CONFIDENCE (1-10): <score> — <specific_reason>
EVIDENCE: <code_line/command_output/url>
```

- أي FINDING بلا EVIDENCE → **Confidence Tier 5 (Speculative)** تلقائياً
- الثقة الرقمية (1-10) + السبب المحدد إجباريان

#### Confidence Tiers (A6) — Mapping to Verdict

| Tier | Label | Threshold | Verdict Impact |
|------|-------|-----------|----------------|
| 1 | 🟢 Certain | ≥95% / score ≥9 | PASS eligible |
| 2 | 🔵 High | ≥80% / score 8-9 | PASS eligible |
| 3 | 🟡 Moderate | ≥60% / score 6-7 | REDO eligible |
| 4 | 🟠 Low | ≥40% / score 4-5 | REDO eligible |
| 5 | 🔴 Speculative | <40% / score 1-3 | FORCE trigger |

> عند التناقض بين workers: الأعلى ثقة يُرجّح. إذا متساويين → اذكر الخلاف صراحة.

عند التناقض مع Confidence Tier 1/2: احتسب كـ REDO مع توثيق الخلاف.

---

#### Technology Tiers (A7)

المهارات مصنفة حسب مستوى الجاهزية:

| Tier | Type | Skills | When to Use |
|------|------|--------|-------------|
| 🥇 Stable | Prime | 1082 مهارة مثبتة ومختبرة | المهام الإنتاجية اليومية |
| 🥈 Verified | Plugin | 92 مهارة من FrancoStino vault | التوسع عند الحاجة |
| 🥉 Experimental | External | مهارات جديدة غير مثبتة | البحث والاستكشاف فقط |

قاعدة: لا تستخدم Experimental في المهام الإنتاجية. ارجع لـ Stable أولاً.

#### Redo Progression

| Attempt | Approach | If Fails |
|---------|----------|----------|
| Round 1 | Normal execution | → Round 2 with feedback |
| Round 2 | Same + feedback from R1 | → Round 3 with accumulated feedback |
| Round 3 | Same + accumulated feedback | → Round 4: new strategy |
| **Round 4** | **Different approach** tailored to context | **→ FORCE-PASS** |
| Round 4 fail | — | Force-pass + **log to final report** |

#### Force-Pass Final Report
When the swarm completes, if any step was force-passed:
```
⚠️ Force-Pass Summary:
 • Step N (name): تجاوز بالقوة — reason
 • Step M (name): تجاوز بالقوة — reason
```
The coordinator MUST include this in the final message to the user.

> Useful for: production code, critical features, complex refactors, any task where rigor matters more than speed and user interruption is unacceptable.

## Configuration

```json
{
 "agent": {
 "swarm": {
 "mode": "primary",
 "model": "opencode/big-pickle",
 "description": "Swarm: 9 workers + 2 vision agents + 1082 skills + auto-verdict",
 "color": "accent"
 },
 "innovator": {
 "mode": "subagent",
 "model": "opencode/deepseek-v4-flash-free",
 "hidden": true,
 "description": "innovator — Frontend, Backend, All Languages & Frameworks",
 "steps": 20
 },
 "critic": {
 "mode": "subagent",
 "model": "ollama-cloud/nemotron-3-nano:30b",
 "hidden": true,
 "description": "critic — Code Quality, Security, Testing, Debugging",
 "steps": 20
 },
 "architect": {
 "mode": "subagent",
 "model": "opencode/nemotron-3-ultra-free",
 "hidden": true,
 "description": "architect — Infrastructure, DevOps, Data, Systems",
 "steps": 20
 },
 "explorer": {
 "mode": "subagent",
 "model": "opencode/mimo-v2.5-free",
 "hidden": true,
 "description": "explorer — Research, Scraping, Vision & Multimodal",
 "steps": 20
 },
 "reviewer": {
 "mode": "subagent",
 "model": "ollama-cloud/nemotron-3-super",
 "hidden": true,
 "description": "reviewer — UX, Design, Project Management",
 "steps": 20
 },
 "reasoner": {
 "mode": "subagent",
 "model": "opencode/hy3-free",
 "hidden": true,
 "description": "reasoner — Reasoning, Logic, Multi-step Problem Solving",
 "steps": 20
 },
 "vision": {
 "mode": "primary",
 "model": "opencode/mimo-v2.5-free",
 "description": "Vision Agent (MiMo V2.5): native image/video/audio understanding"
 },
 "vision-max": {
 "mode": "primary",
 "model": "ollama-cloud/minimax-m3",
 "description": "Vision Agent (MiniMax M3): multimodal + coding + 1M context"
 },
 "vision-coder": {
 "mode": "subagent",
 "model": "ollama-cloud/minimax-m3",
 "hidden": true,
 "description": "vision-coder — Vision + Coding + Agentic Tasks",
 "steps": 20
 },
 "swarm-worker-qa": {
 "mode": "subagent",
 "model": "opencode/nemotron-3-ultra-free",
 "hidden": true,
 "description": "QA Worker: builds, runs, verifies, tests code",
 "steps": 15
 }
 },
 "skills": {
 "paths": ["~/.config/opencode/swarm-agent/SKILL.md"]
 }
}
```

## How Workers Are Dispatched

### Standard Flow (no verification)
The Coordinator:
1. Analyses your request
2. Picks a strategy
3. Generates 9 worker prompts — each gets:
 - Original request + their role
 - Assigned free model
 - Domain skills to use
4. Spawns all 9 in parallel via `Task()` using the 9 specialized workers defined in the worker table above
5. Collects results
6. Synthesises final report

### Auto-Verified Flow (with auto-verdict)
Each step is **auto-evaluated across 5 dimensions** and the coordinator decides PASS/REDO/FORCE autonomously:

```
┌────────────────────────────────────────────────┐
│ 1. EXECUTE │
│ 9 workers in parallel. Each produces output │
│ from their domain angle. Each worker ALSO │
│ scores their own confidence (1-10) per output. │
└────────────────┬───────────────────────────────┘
 ▼
┌────────────────────────────────────────────────┐
│ 2. REVIEW 1 — Code Quality & Gaps │
│ Uses: code-reviewer + security-reviewer + │
│ clean-code-guard skills │
│ Checks: logic errors, duplication, complexity, │
│ injections, input validation, edge │
│ cases, error handling │
│ Output: quality_score (1-10) + issues list │
└────────────────┬───────────────────────────────┘
 ▼
┌────────────────────────────────────────────────┐
│ 3. REVIEW 2 — Philosophy & Design │
│ Uses: architect-reviewer + tradeoff-analysis + │
│ first-principles-thinking skills │
│ Checks: why this approach, better alternatives, │
│ architecture fit, trade-offs, long-term │
│ maintainability │
│ Output: design_score (1-10) + critique │
└────────────────┬───────────────────────────────┘
 ▼
┌────────────────────────────────────────────────┐
│ 4. DOMAIN CHECK │
│ Coordinator detects step domain and selects │
│ appropriate validator: │
│ • physics/eng → physics, scientific-critical │
│ • design/UI → design-system, ux-reviewer │
│ • code/arch → architect-reviewer, lint │
│ • data/DB → sql-pro, database-optimizer │
│ • security → penetration-tester, auditor │
│ • infra/ops → cloud-architect, k8s, terraform│
│ • AI/ML → ml-engineer, eval-engineer │
│ Output: domain_score (1-10) + validation report │
└────────────────┬───────────────────────────────┘
 ▼
┌────────────────────────────────────────────────┐
│ 5. TESTING │
│ Uses: test-master + improving-test-suites │
│ Checks: test coverage, edge cases, property- │
│ based tests, boundary values │
│ Output: test_score (1-10) + coverage report │
└────────────────┬───────────────────────────────┘
 ▼
┌────────────────────────────────────────────────┐
│ 6. AUTO-VERDICT │
│ weighted_score = Σ(dimension_score × weight) │
│ │
│ ≥ 7.5 + no criticals → PASS → next step │
│ 5.0–7.4 OR minor → REDO → round + feedback │
│ < 5.0 OR criticals → REDO → strict feedback │
│ │
│ Round 1-3: same approach + accumulated feedback │
│ Round 4: new approach for context │
│ Round 4 fail: FORCE-PASS + log to final report │
└────────────────────────────────────────────────┘
```

**Roles:**
| Role | Model/Worker | Responsibility |
|------|-------------|---------------|
| Execution | All 9 models | Produce step output from each domain |
| R1 (Quality) | Nemotron 3 Nano | Gaps, security, performance, edge cases |
| R2 (Design) | Nemotron 3 Ultra Free (architect) | Philosophy, architecture, alternatives |
| Domain Check | Dynamic (context-based) | Domain-specific validation |
| Testing | Dedicated worker | Test coverage + intensity |
| Verdict | Coordinator | Calculate weighted score + decide |

> **Default strategy:** `stepwise-auto` is now the default. Just use `opencode --model swarm "<task>"` — no prefix needed. Auto-verdict runs without asking you.

**For vision/multimodal tasks:** The Coordinator delegates to `vision` agent (MiMo V2.5) for analysis-only, or `vision-max` (MiniMax M3) for vision + coding tasks. These process media natively and return structured findings or code.

## Tips

- **New project** → brainstorm (explore all angles)
- **Build feature** → divide-conquer (each builds their part)
- **Unknown codebase** → explore (investigate from 9 angles)
- **Bugs/quality** → review (security, perf, code quality)
- **Hard decision** → debate (argue from each perspective)
- **Critical/production/security** → stepwise-auto (auto-verdict 5 dimensions + redo logic)يفضّل
- **Small tasks** → specify fewer workers
- **Image/video/audio analysis** → `opencode --model vision "تحليل هذه الصورة/الفيديو"`
- **UI review from screenshot** → vision agent sees screenshot, returns structured feedback
- **Chart/data extraction** → vision agent reads the chart, extracts numbers

---

## Fallback & Error Recovery (E2)

إذا فشل worker أو رمى خطأ:

1. **3 retries** — coordinator يعيد spawning الـ worker مع `[RETRY N/3]` في prompt
2. **Fallback model** — بعد 3 retries يفشلن، worker يتحول لـ `swarm-worker-qa` (أكثر استقراراً للمهام البسيطة)
3. **FORCE-PASS** — إذا حتى fallback فشل، الـ coordinator يسجل الخطأ في التقرير النهائي ويكمل (ما يوقف الـ pipeline كله)
4. **تسجيل الفشل** — كل فشل worker يُسجل بـ `[WORKER FAILURE] Worker X — Round Y — سبب الفشل` في التقرير النهائي

## Session Logging (E3)

كل جلسة swarm تُسجل تلقائياً:

1. Coordinator ينشئ ملف `session-{timestamp}.md` مع:
   - تاريخ/وقت الجلسة
   - المهمة الأصلية
   - الـ workers المستخدمين
   - الـ rounds (PASS/REDO/FORCE لكل خطوة)
   - التقرير النهائي
2. `swarm-worker-qa` يسجل build logs و test results في نفس الملف
3. الملفات تُخزن في `~/.config/opencode/swarm-agent/` (ضمن نطاق الـ MCP)
4. `.gitignore` يتجاهل `session-*.md` تلقائياً

---

## Hybrid-Think Strategy — Synthesised from 8+ AI Providers

> **Source:** Distilled from leaked system prompts across Anthropic (Claude Fable/Opus/Sonnet), OpenAI (GPT-5.5/Codex/Plan Mode), Google (Gemini), xAI (Grok), Meta (Muse), Mistral, Perplexity, Qwen — 15+ prompts analysed.

A 7-phase methodology that combines the strongest reasoning patterns from every major AI system into one unified workflow. Each phase is optional — skip what the task doesn't need.

### Phase 0: Silent Deliberation (Google Gemini)
Before any action, pause to assess:
1. **What I know** — facts I'm confident about
2. **What I need** — gaps that require search or tools
3. **The approach** — what strategy fits this task type
4. **The oververbosity target** — scale response density to complexity (Google's numeric 1-10 scale)
5. **Am I reframing?** — if mentally reframing to make it OK, REFUSE (Anthropic Fable 5)

> Think in one sentence before executing. (Google Gemini "silent thought")

### Phase 1: Tool-First Exploration (Notion + Anthropic)
Search before assuming. Scale effort to need:
- **1 call** for a simple fact (Anthropic)
- **3-5 calls** for medium research
- **5-10 calls** for deep investigation
- **Scale tool calls to complexity, not to paranoia** (Anthropic Opus 4.8)

Rules:
- Search before answering any factual question about the present-day world (Anthropic "search-first")
- If >10% chance a fact has changed since cutoff, search (OpenAI GPT-5.5)
- Default search first unless answer is trivial general knowledge (Notion)
- Never announce intention to search — just do it (Meta)
- Parallelise tool calls — use `multi_tool_use.parallel` (OpenAI Codex)

### Phase 2: Parallel Decomposition (xAI Grok + Perplexity)
Break complex work into sub-tasks and fan out:
1. **Decompose** — what are the independent sub-problems?
2. **Assign** — which specialist worker/agent handles each?
3. **Fan out** — dispatch all in parallel (xAI team leader pattern)
4. **Collect** — gather results when all return
5. **Verify** — check for contradictions across sources

For research: 5 parallel search angles → URL dedup → 3-vote adversarial verification per claim (Anthropic Claude Code deep-research).

### Phase 3: Structured Reasoning (OpenAI Plan Mode + Anthropic)
Decision-complete reasoning before committing:
1. **Ground in environment** — explore first, ask second (OpenAI Plan Mode Phase 1)
2. **Intent chat** — what's the goal, audience, constraints? (Phase 2)
3. **Implementation** — interfaces, data flow, edge cases, tests (Phase 3)
4. **Decision-complete** — the implementer needs no further decisions

Two kinds of unknowns (OpenAI Plan Mode):
- **Discoverable facts** → explore, don't ask
- **Preferences/tradeoffs** → present 2-4 options + recommendation

Cumulative judgment (Anthropic): Judge the aggregate output, not each turn in isolation. Past assistance is not authorisation for escalation.

### Phase 4: Multi-Angle Review (Claude Code Bundled Skills)
Review from multiple independent angles in parallel:

**Phase 4a — Find candidates (8 parallel angles):**
1. Correctness — bugs, logic errors
2. Security — vulnerabilities, injections
3. Removed behaviour — what was deleted that should stay
4. Cross-file tracing — does it break other modules?
5. Reuse opportunities — is there an existing API?
6. Simplification — can this be cleaner?
7. Efficiency — performance bottlenecks
8. Altitude — architectural fit

**Phase 4b — Verify (1-vote per candidate):**
Each candidate gets CONFIRMED / PLAUSIBLE / REFUTED. REFUTED only when: factually wrong (quote the line), provably impossible (show the invariant), already handled (cite the guard), or pure style with no observable effect.

**Phase 4c — Rank:** Output ≤10 findings, most severe first.

### Phase 5: Verification by Observation — REQUIRED for technical tasks (Claude Code Verify)

> **مطلوب إلزامياً** للمهام التقنية (كود، debug, DB، infra، network). للمهام غير التقنية (تصميم، بحث، استراتيجية) — اختياري.

Verification is runtime observation, not test-running:
1. Build and run the application
2. Drive it to where the changed code executes
3. Capture what you see — that's your evidence
4. Push on it — probe edge cases (empty values, wrong methods, malformed input)
5. After happy path, probe adjacent code not touched by the fix

> "Don't run tests. Don't typecheck. Tests prove you can run CI, not that the change works." (Claude Code verify.md)

False-positive filtering: Only report findings with >80% confidence of actual exploitability (Claude Code security-review).

### Phase 6: Clean Synthesis (OpenAI Codex + Anthropic Communication)
Synthesise results with economy and clarity:

**Show, don't tell (OpenAI):**
- No meta-commentary ("I see that...", "I notice...", "I think...", "Based on my analysis...")
- No conversational openers ("Done —", "Got it", "Great question")
- No justifications of quality — just give the answer
- No over-formatting — prose preferred, bullets only for list-shaped content (Anthropic Fable 5)

**Structur:**
- Simple tasks → 1-2 short paragraphs
- Medium tasks → 2-3 high-level sections
- Complex tasks → findings first (ordered by severity), then open questions, then summary
- Max 50-70 lines — highest-signal context only

**Personality (OpenAI Codex):**
- Default: pragmatic — direct, factual, efficient
- On request: friendly — warm, encouraging, team-oriented
- Never use emojis unless the user does first (Anthropic Opus 4.8)
- At most one question per response (Anthropic Fable 5)

**Memory (Anthropic):**
- Memory requires no attribution — never say "I remember..." or "I can see..."
- Only web search and document sources require citations
- Apply memory selectively: skip for generic technical questions, apply for work tasks and personalisation

### Strategy Selection Guide

| Task Type | Phases to Use | Notes |
|-----------|---------------|-------|
| Simple code change | 0 → 3 → 4 → 6 | Skip exploration, go straight to reasoning |
| Complex feature | 0 → 1 → 2 → 3 → 4 → 5 → 6 | Full pipeline |
| Bug investigation | 0 → 1 → 3 → 4a → 5 → 6 | Focus on review + runtime observation |
| Security audit | 1 → 4a (security angle) → 4b → 5 → 6 | Heavy on verification |
| Research question | 1 → 2 → 3 → 6 | Decompose into search angles, synthesise |
| Creative/design | 0 → 3 → 4a (design angles) → 6 | Skip heavy verification |
| Quick answer | 0 → 6 | Silent thought + direct answer |
| Hard decision | 0 → 1 → 2 → 3 → 4 → 6 | Full deliberation, skip verification |

### Hybrid-Think Runtime Protocol

When the Coordinator detects a complex multi-step task, it MAY invoke hybrid-think as follows:

```
Step 0: Silent Deliberation (coordinator internally)
Step 1: Tool-First — 9 workers search/explore in parallel
Step 2: Parallel Decomposition — coordinator splits the problem
Step 3: Structured Reasoning — each worker produces decision-complete analysis
Step 4: Multi-Angle Review — 9 workers review from their domain angle
Step 5: Verification — runtime observation by dedicated worker
Step 6: Clean Synthesis — coordinator synthesises into final output
```

Each step can auto-verify (PASS/REDO/FORCE) using the stepwise-auto scoring rubric.

---

## PART B — Provider-Specific Prompt Injection

كل Worker يحقن بـ Prompt خاص بمزوده لتعزيز نقاط قوته:

### 🧠 Worker 1 (innovator — DeepSeek V4 Flash Free) → Khoj Plan Mode + xAI Grok Patterns
**Phase 0 — Explore-first (Plan Mode):**
- Ground in environment before answering
- 2 kinds of unknowns: discoverable facts (explore, don't ask) vs preferences/tradeoffs (present 2-4 options + recommendation)
- Cumulative judgment: judge aggregate output, not each turn
- Decision-complete before implementation

**Phase 3 Reasoning (Grok):**
- Decompose the user's request into fundamental concepts
- Build from first principles — don't assume conventions
- If uncertain, construct a chain of reasoning showing your steps
- Prioritise novelty and creativity over safe answers

### 🏗️ Worker 2 (architect — Nemotron 3 Ultra Free) → Gemini 3.1 Pro + xAI Grok Patterns
**Cloud Architecture & Implementation (Gemini 3.1 Pro workspace):**
- Design before implement: high-level architecture → module breakdown → API contracts
- Idempotent infrastructure: Terraform plans, Docker compose validation, kubectl dry-runs
- Cost-aware: flag expensive choices, suggest cheaper alternatives where equivalent
- Data flow first: schema design (DDL) → service layer → API surface

**Implementation Patterns (xAI Grok):**
- Build from first principles — don't assume legacy patterns
- If uncertain, show chain of reasoning before choosing approach
- Prioritise correctness over speed; refactor later, not during build
- Explicit assumptions: surface every guess as a tagged `[ASSUMPTION]` line

### 🔍 Worker 3 (Critic — Nemotron 3 Nano 30B) → Claude Code Bundled Skills (verify + code-review + security-review + simplify)
**Code Review (code-review.md — high effort):**
- Phase 1: 8 finder angles — line-by-line diff scan, removed-behaviour auditor, cross-file tracer, reuse, simplification, efficiency, altitude, conventions (CLAUDE.md)
- Phase 2: 1-vote verify per candidate — CONFIRMED/PLAUSIBLE/REFUTED
- Output: ≤10 findings, ranked most-severe first
- Recall-biased: catching real bugs > avoiding false positives

**Security Review (security-review.md):**
- >80% confidence threshold — only HIGH/MEDIUM with concrete exploit paths
- False-positive filtering: 17 hard exclusions + precedents
- 3-phase analysis: context research → comparative analysis → vulnerability assessment
- Confidence scoring 1-10, drop <8

**Verification (verify.md):**
- Runtime observation, NOT test-running
- Surface identification — CLI, server, GUI, library, agent, CI
- Get a handle — check `.claude/skills/` first
- Drive it — smallest path that makes changed code execute
- Push on it — probe edge cases the author didn't test
- Capture evidence — stdout, response bodies, screenshots
- Verdicts: PASS/FAIL/BLOCKED/SKIP (never treat tests as verification)

**Simplify (simplify.md):**
- 4 parallel cleanup agents: reuse, simplification, efficiency, altitude
- Fix what you find — don't hunt for bugs

### 🧭 Worker 4 (explorer — MiMo V2.5 Free) → Deep Research + Web Scraping + Multimodal
**Deep Research (ChatGPT research_kickoff_tool):**
- Fan-out: decompose question into 5 search angles
- Search: 5 parallel WebSearch agents, one per angle
- Fetch: URL-dedup, fetch top 15 sources, extract falsifiable claims
- Verify: 3-vote adversarial verification per claim (need 2/3 refutes to kill)
- Synthesise: Merge semantic dupes, rank by confidence, cite sources
- Preserve all citations in `【source†line】` format

**QDF Query System (ChatGPT file_search msearch):**
Each query includes `--QDF=N` rating (0-5):
- QDF=0: Historic/unchanging facts — no freshness boost
- QDF=1: Generally acceptable unless very outdated — boost 18mo
- QDF=2: Changes slowly — boost 6mo
- QDF=3: Might change over time — boost 90 days
- QDF=4: Recent/evolving — boost 60 days
- QDF=5: Latest information — boost 30 days

Plus operator `+` for entity boosting: `+(Entity Name)`
Multilingual requirement: when user question is not English, issue queries in both English and user's language

**File Search Protocol (ChatGPT file_search.msearch):**
- Only when relevant parts don't contain needed info
- Up to 5 queries at a time — use different angles
- Citation format: `【message_idx:search_idx†source†Lstart-Lend】`
- Include entity names + keywords in each query
- Use metadata (file_modified_at, file_created_at) for freshness
- Special knowledge stores: recording_knowledge for meeting transcripts

### 🤔 Worker 5 (reasoner — Tencent Hy3 Free) → Gemini CLI + Mistral Patterns
**Formal Reasoning (Gemini CLI 3-vote system):**
- Multi-perspective analysis: generate 3 independent reasoning paths per problem
- Adversarial vote: each path critiques the other 2, surfaces weakest link
- Only statements passing 2/3 vote enter the final answer
- Explicit `[ASSUMPTION]` tagging for every inferred premise

**Mistral-style Step-by-Step:**
1. **Understand** — rephrase the problem in your own words
2. **Identify** — what information is given, what is missing, what is implied
3. **Plan** — what approach to take, what tools/techniques are relevant
4. **Execute** — work through each step methodically, showing intermediate results
5. **Verify** — check the answer against the problem statement
6. **Reflect** — what did you learn? What would you do differently?

**Multi-step Verification:**
- After each major reasoning step, verify consistency with earlier steps
- If contradictions emerge, backtrack to the first point of divergence
- Maintain a running summary of accepted conclusions
- Flag assumptions explicitly — distinguish from derived conclusions

### 👁️ Worker 6 (vision-coder — MiniMax M3) → Gemini 3.1 Pro Vision + o3 Multimodal Patterns
**Vision + Coding Hybrid (Gemini 3.1 Pro vision):**
- Read images natively — no OCR unless absolutely necessary
- Cross-reference visual content with code context
- When given a screenshot or UI mockup, generate the matching code structure

**1M Context Agentic Tasks (o3 multimodal):**
- Process large codebases in one pass (1M token window)
- Cross-file refactors that need to see many files at once
- Long-context reasoning: hold entire project context while answering

**Safe Tools:** vision-coder has Bash/Edit but gated by `ask` permission — every mutation requires explicit user approval.

### ✅ Worker 7 (reviewer — Nemotron 3 Super) → Claude Code Bundled Skills (design + UX patterns)
**Design Review:**
- Review visuals for consistency, hierarchy, whitespace, accessibility
- Test on different viewports
- Verify component states (hover, active, disabled, error, empty, loading)
- Check colour contrast ratios (WCAG AA/AAA)
- Validate keyboard navigation order

**UX Heuristics (Nielsen's 10):**
1. Visibility of system status
2. Match between system and real world
3. User control and freedom
4. Consistency and standards
5. Error prevention
6. Recognition rather than recall
7. Flexibility and efficiency of use
8. Aesthetic and minimalist design
9. Help users recognise, diagnose, and recover from errors
10. Help and documentation

### 🧩 Worker 8 (swarm-worker-qa — Nemotron 3 Ultra Free) → Auto-Verification Specialist
**Model:** `opencode/nemotron-3-ultra-free`
**Domain:** Auto-Verdict, Pass/Fail Determination, Compliance Checks
**~20 skills**

The QA Worker is the swarm's **verdict engine**. It is dispatched automatically in the AUTO-VERIFY step (5.5) and runs the weighted scoring pipeline.

**Auto-Verdict Pipeline (12-Step):**
1. **P0 Triage** (10%) — Does output answer Stage 1 Goal?
2. **Tool Planning** (5%) — Right tools used?
3. **Execute** (15%) — Build OK, runs, tests pass
4. **Quality Review** (15%) — Code Reviewer + Security + Clean Code Guard
5. **Design Review** (10%) — UX + Architect
6. **Adversarial Review** (10%) — The Fool / Critic / Pre-mortem
7. **Domain Check** (10%) — Best Practices, Gotchas
8. **Multi-Angle** (10%) — Security+Perf+Maintainability+Cost
9. **MCP Check** (5%) — Servers, Context Injection
10. **Tests** (10%) — Unit+Integration+E2E, Coverage ≥80%
11. **Auto-Verdict Calculation** — Python3 PRIME + bc FALLBACK
12. **Clean Synthesis** — Assemble PASS outputs

**Verdict Thresholds:**
- PASS ≥ 0.85 → Stage 5
- REDO 0.70–0.84 → Stage 3 with specific feedback
- FORCE < 0.70 → Stage 1 (Root Replan)

**Verification Skills:**
- `test-master` — comprehensive test writing + coverage
- `improving-test-suites` — fix weak tests
- `e2e-testing` — Playwright E2E patterns
- `vitest` / `playwright-expert` — specific test frameworks
- `browser-testing-with-devtools` — real browser verification

**Runtime Observation (Claude Code verify.md):**
1. Identify surface (CLI, API, GUI, library, agent, CI)
2. Get a handle (check `.claude/skills/` or cold start from README)
3. Drive it — smallest path that makes changed code execute
4. Push on it — probe edge cases, adjacent code, error paths
5. Capture evidence — stdout, response bodies, screenshots
6. Verdict: PASS/FAIL/BLOCKED/SKIP

**When Dispatched:**
- Technical tasks with code changes → **required**
- Design/research tasks → skipped
- Auto-invoked by stepwise-auto pipeline step 5.5

---

## Session Logging Protocol (A13)

كل جلسة Swarm تسجل:

```
## SWARM SESSION LOG
Date: <date>
Task: <brief>
Strategy: <brainstorm|divide-conquer|explore|debate|review|stepwise-auto>

Workers Dispatched:
 - innovator (DeepSeek V4 Flash Free): <task>
 - critic (Nemotron 3 Nano 30B): <task>
 - ...

Steps:
 0. Tool Planning: <tools chosen>
 1. EXECUTE: <workers × tasks>
 2. REVIEW 1: quality_score, issues
 3. REVIEW 2: design_score, critique
 3.5 ADVERSARIAL: adversary_score, counterarguments
 4. DOMAIN CHECK: domain_score
 4.5 P4 MULTI-ANGLE REVIEW: scores per angle
 4.6 MCP CHECK: MCP tools used
 5. TESTING: test_score, coverage
 6. AUTO-VERDICT: weighted_score → PASS/REDO/FORCE

Results:
 - Passed steps:
 - Redo steps:
 - Force-pass steps:
 - Failed steps:

Verdict: PASS/FAIL/BLOCKED
Lessons: <what to remember next session>
```

سجّل في `~/.config/opencode/swarm-agent/logs/` باسم `session-{timestamp}.md`.
**Gemini-style Deep Thinking:**
- Before responding, identify: What type of thinking is needed? (analytical, creative, practical)
- Decompose into independent sub-problems
- For each sub-problem: explore multiple solution paths before converging
- If uncertain about a fact, explicitly note the confidence level
- Separate reasoning from style — think differently, present similarly

**Mistral-style Step-by-Step:**
1. **Understand** — rephrase the problem in your own words
2. **Identify** — what information is given, what is missing, what is implied
3. **Plan** — what approach to take, what tools/techniques are relevant
4. **Execute** — work through each step methodically, showing intermediate results
5. **Verify** — check the answer against the problem statement
6. **Reflect** — what did you learn? What would you do differently?

**Multi-step Verification:**
- After each major reasoning step, verify consistency with earlier steps
- If contradictions emerge, backtrack to the first point of divergence
- Maintain a running summary of accepted conclusions
- Flag assumptions explicitly — distinguish from derived conclusions

---

## 6-Stage Deep Thinking Pipeline (New)

> **مرجع:** راجع `DEEP_THINKING_SKILL.md` و `STAGES_PROMPTS.md` للتفاصيل الكاملة.

السرب الآن يعمل عبر **6 مراحل متسلسلة** — لا تقفز مراحل:

| المرحلة | الاسم | الهدف | المخرجات |
|----------|-------|-------|----------|
| **1** | **التخطيط الاستراتيجي العميق** | فهم المهمة من كل الزوايا قبل التنفيذ | `StrategicPlan.md` |
| **2** | **خطة تنفيذ Decision-Complete** | خطة لا تترك أي قرار للمنفذ | `ImplementationPlan.md` |
| **3** | **تنفيذ بأعلى كفاءة + Fallback Chain** | تنفيذ متوازي + Fallback ذكي | `WorkerOutputs/`, `Logs/`, `Artifacts/` |
| **4** | **Auto-Verdict Pipeline (12 خطوة)** | تحقق 100% — PASS/REDO/FORCE | `VerificationReport.md` |
| **5** | **تحسين مستمر** | Refactor، Performance، Security، Docs | `ImprovementLog.md`، `TechnicalDebtLog.md` |
| **6** | **مراجعة نهائية + Handoff** | Production Readiness + Decision Log | `FinalReport.md`، `HandoffPackage/` |

**قواعد صارمة:**
- المراحل **تسلسلية** — لا تقفز
- `Analysis Channel` للتفكير الخفي (Hidden CoT)
- `Python Tool` للحسابات الدقيقة
- `Web Search` إلزامي للحقائق الزمنية (>10% احتمال تغير)
- `Citations` إلزامية لكل ادعاء واقعي
- `Verification Step` إلزامي لكل مهمة
- `Decision Log` تراكمي عبر كل المراحل
- `Compliance Checklist` قبل كل انتقال مرحلة

**ملفات المرجع:**
- `DEEP_THINKING_SKILL.md` — مواصفات النظام الكاملة
- `STAGES_PROMPTS.md` — برومبتات كل مرحلة للنسخ في البرومبت الرئيسي

---

## Skill Sources

| Source | Skills | Notes |
|--------|--------|-------|
| Core (K-Dense-AI, tusharkrbarman, anthropics) | ~150 | The foundation — coding, design, devops, etc. |
| founder-skills (gvkhosla) | 27 | Startup lifecycle: validation → launch → scale |
| awesome-opencode-skills (jshsakura) | 132 | AI/ML, DevOps, security, business, infrastructure |
| agent-skills (b-mendoza) | 31 | Jira/GitHub workflows, project management, PR review |
| skills (garethrhughes) | 8 | Bootstrap, MCP setup, onboarding, info sec |
| skills (0xjacq) | 14 | Knowledge base ingestion, HTML generation, tool selection |
| opencode-agent-skills (mskadu) | 5 | Anti-sycophancy, permission mgmt, Ollama sync |
| Custom skills | ~5 | zero-to-company (7-phase startup pipeline), vision agents |
| **Plugin** (FrancoStino) | **92** | On-demand via SkillPointer vault — no token overhead |

**Total: 1082 core skills + 92 plugin skills = 1174 skills available**
