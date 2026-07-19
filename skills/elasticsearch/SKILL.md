---
name: elasticsearch
description: Configures Elasticsearch clusters, mappings, queries, aggregations, and analysis pipelines.
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/opencode
  version: "1.0.0"
  domain: search
  triggers: Elasticsearch, ES, search, index, mapping, query DSL, aggregation, analyzer, Kibana, cluster
  role: specialist
  scope: implementation
  output-format: code
  related-skills: kibana, logstash, algolia, meilisearch, docker-compose
---

# Elasticsearch

Elasticsearch is a distributed, RESTful search and analytics engine capable of full-text search, structured queries, real-time aggregations, and vector/kNN search. It is the core of the Elastic Stack alongside Kibana, Logstash, and Beats, and is suited for logging, metrics, e-commerce search, and application monitoring.

## When to Use This Skill

- Designing index mappings with proper field types, analyzers, and `dynamic` templates for a new search use case
- Writing complex Query DSL — boolean queries, full-text search, span queries, geo queries, and fuzzy matching
- Building real-time aggregations for dashboards — terms, date histograms, percentiles, and bucket/sibling pipelines
- Configuring cluster topology — node roles, shard allocation, replicas, and snapshot/restore lifecycle policies
- Integrating with Kibana for data visualization, Canvas, Lens, or Alerting rules

## Key Capabilities

- Index mappings and settings — Define explicit field types (`keyword`, `text`, `geo_point`, `nested`, `dense_vector`), analyzers, and dynamic templates
- Query DSL — Compose `bool`, `match`, `term`, `range`, `fuzzy`, `wildcard`, `geo_distance`, `knn` queries with boosting and rescore
- Aggregation framework — Run metric (`avg`, `cardinality`), bucket (`date_histogram`, `terms`, `geotile`), and pipeline (`moving_avg`, `bucket_script`) aggregations
- Analysis and tokenization — Configure character filters, tokenizers, and token filters (stemming, stop words, synonyms) per index
- Cluster and index lifecycle — Manage ILM policies for hot-warm-cold-frozen tiers, force merge, rollover, and snapshot repositories

## Best Practices

- Design mappings up front — once an index has data, changing a field type requires reindexing; use `index: false` for fields you only store (not search)
- Size shards between 10-50 GB to balance query performance and cluster overhead; use ILM for rolling indices
- Avoid wildcard and regex queries in production — they skip the inverted index and can cause cluster slowdowns; prefer `match_phrase_prefix` or `ngram` analyzers instead
