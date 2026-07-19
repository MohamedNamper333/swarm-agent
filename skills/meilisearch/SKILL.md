---
name: meilisearch
description: Deploys and configures Meilisearch for typo-tolerant full-text search with filtering and sorting.
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/opencode
  version: "1.0.0"
  domain: search
  triggers: Meilisearch, search, typo-tolerant, full-text search, filtering, sorting, ranking, index
  role: specialist
  scope: implementation
  output-format: code
  related-skills: algolia, elasticsearch, docker-compose
---

# Meilisearch

Meilisearch is an open-source, self-hosted search engine with instant typo-tolerant full-text search, faceted filtering, geo-search, and customizable ranking rules. It provides a straightforward REST API, built-in dashboard, and language-aware tokenization for 17+ languages.

## When to Use This Skill

- Deploying and configuring a self-hosted Meilisearch instance via Docker or bare metal
- Indexing documents and configuring searchable, filterable, and sortable attributes
- Tuning relevance through ranking rules, custom order, and proximity weighting
- Implementing faceted search with drill-down filters for e-commerce or directory applications
- Setting up tenant tokens for multi-tenant search with per-user document visibility

## Key Capabilities

- Index and document management — Create indexes, add/update/delete documents as JSON, and configure primary key selection
- Ranking rule customization — Define the order of relevance criteria (words, typo, proximity, attribute, sort, exactness)
- Faceted search — Mark attributes as filterable and sortable; apply facet distributions and drill-down filters with `filter` in queries
- Typo tolerance — Configure `minWordSizeForTypos`, disable typos on specific attributes, or set per-index typo levels
- Tenant token security — Generate signed API keys with restricted index and filter access for multi-tenant use cases

## Best Practices

- Set `MAX_INDEX_SIZE` based on available RAM — Meilisearch keeps the entire index in memory for fast lookups
- Define `searchableAttributes` explicitly rather than relying on the default (all attributes) for cleaner relevance
- Use separate indexes for different document types (products, articles, users) rather than mixing them with filter-based segregation
