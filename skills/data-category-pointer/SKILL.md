---
name: data-category-pointer
description: "Pointer to a library of 19 specialized Data skills. Use when working on data-related tasks."
risk: none
---

# Data Capability Library 🎯

This is a **pointer skill**. The 19 specialized Data skills are stored in a hidden vault to keep your startup context minimal.

## Available skills in this category

- **alpha-vantage** — Access 20+ years of global financial data: equities, options, forex, crypto, commodities, economic indicators, and 50+ technical indicators.
- **amplitude-automation** — Automate Amplitude tasks via Rube MCP (Composio): events, user activity, cohorts, user identification. Always search tools first for current schemas.
- **analytics-product** — Analytics de produto — PostHog, Mixpanel, eventos, funnels, cohorts, retencao, north star metric, OKRs e dashboards de produto.
- **analytics-tracking** — Design, audit, and improve analytics tracking systems that produce reliable, decision-ready data.
- **arrowspace** — Spectral vector search using graph Laplacian eigenstructure. Use when cosine/L2 similarity misses latent structure in your embeddings.
- **data-engineer** — Build scalable data pipelines, modern data warehouses, and real-time streaming architectures. Implements Apache Spark, dbt, Airflow, and cloud-native data platforms.
- **dbt-transformation-patterns** — Production-ready patterns for dbt (data build tool) including model organization, testing strategies, documentation, and incremental processing.
- **firecrawl-scraper** — Deep web scraping, screenshots, PDF parsing, and website crawling using Firecrawl API. Use when you need deep content extraction from web pages, page interaction is required (clicking, scrolling, etc.), or you want screenshots or PDF parsing.
- **mixpanel-automation** — Automate Mixpanel tasks via Rube MCP (Composio): events, segmentation, funnels, cohorts, user profiles, JQL queries. Always search tools first for current schemas.
- **monte-carlo-monitor-creation** — Guides creation of Monte Carlo monitors via MCP tools, producing monitors-as-code YAML for CI/CD deployment.
- **monte-carlo-validation-notebook** — Generates SQL validation notebooks for dbt PR changes with before/after comparison queries.
- **posthog-automation** — Automate PostHog tasks via Rube MCP (Composio): events, feature flags, projects, user profiles, annotations. Always search tools first for current schemas.
- **segment-automation** — Automate Segment tasks via Rube MCP (Composio): track events, identify users, manage groups, page views, aliases, batch operations. Always search tools first for current schemas.
- **segment-cdp** — Expert patterns for Segment Customer Data Platform including Analytics.js, server-side tracking, tracking plans with Protocols, identity resolution, destinations configuration, and data governance best practices.
- **spark-optimization** — Optimize Apache Spark jobs with partitioning, caching, shuffle optimization, and memory tuning. Use when improving Spark performance, debugging slow jobs, or scaling data processing pipelines.
- **sql-pro** — Master modern SQL with cloud-native databases, OLTP/OLAP optimization, and advanced query techniques. Expert in performance tuning, data modeling, and hybrid analytical systems.
- **sql-sentinel** — Audit SQL for the cost & performance anti-patterns that burn warehouse credits. Scores warehouse health 0-100 and outputs a prioritized cost-reduction plan for BigQuery, Snowflake, Redshift, and Postgres.
- **web-scraper** — Web scraping inteligente multi-estrategia. Extrai dados estruturados de paginas web (tabelas, listas, precos). Paginacao, monitoramento e export CSV/JSON.
- **x-twitter-scraper** — X/Twitter automation skill for tweet search, follower export, posting, DMs, webhooks, MCP, SDKs, Hermes Tweet, and TweetClaw.

## How to load a skill

1. Identify the skill name above matching your task.
2. Use `view_file` to read its `SKILL.md` from the vault:
   `/home/kali/.config/opencode/skill-libraries/data/<skill-name>/SKILL.md`
3. Follow those instructions to complete the request.

**Vault path:** `/home/kali/.config/opencode/skill-libraries/data`

> Do not guess best practices — always read from the vault first.

> ⚠️ **Anti-loop guard**: Do NOT invoke skills recursively or check for applicable skills before every response. Each skill should be loaded at most once per user request. If you have already identified and loaded the relevant skill for this task, proceed with execution — do not re-scan for skills.
