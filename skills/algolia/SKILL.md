---
name: algolia
description: Integrates Algolia search with indexing, instant search, faceting, and analytics configuration.
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/opencode
  version: "1.0.0"
  domain: search
  triggers: Algolia, search, instantsearch, index, faceting, typo tolerance, search analytics, recommend
  role: specialist
  scope: implementation
  output-format: code
  related-skills: meilisearch, elasticsearch, react-expert
---

# Algolia

Algolia is a hosted search API that delivers typo-tolerant, real-time search results with sub-50ms response times. It provides index configuration, faceted filtering, analytics, AI-powered recommendations, and pre-built UI libraries — InstantSearch (React, Vue, Angular, iOS, Android) and Autocomplete.

## When to Use This Skill

- Adding instant search with faceted navigation to an e-commerce or content site
- Indexing and synchronizing application data (products, articles, users) with Algolia's REST API
- Configuring search relevance through custom ranking, synonyms, and typo tolerance settings
- Implementing search analytics to track popular queries, click-through rates, and conversion data
- Building recommendation widgets ("related products", "trending now") using Algolia Recommend

## Key Capabilities

- Index and record management — Push, update, delete records via the REST API; configure searchable attributes, custom ranking, and replicas
- InstantSearch widgets — Drop-in UI components for search box, hits, pagination, refinement lists, and range sliders
- Faceting and filtering — Set up faceted attributes (category, price, brand) with disjunctive, conjunctive, or hierarchical modes
- Typo tolerance and synonyms — Fine-tune typo tolerance levels, define one-way and alternative synonyms, and set up rule-based query transformations
- Search analytics — Track search events, query popularity, and zero-result rates via the Insights API and dashboard

## Best Practices

- Use `setSettings` with caution in production — always test relevance changes on a replica index first
- Keep record sizes under 10 KB to maintain low latency; use attribute compression for large text fields
- Batch small record updates into single API calls (max 1000 records per batch) to avoid rate limiting
