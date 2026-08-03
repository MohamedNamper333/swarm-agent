---
name: redis
description: Use when integrating Redis for caching, pub/sub messaging, session management, rate limiting, and distributed data structures. Invoke for cache strategies, Redis client configuration, sorted sets, streams, Lua scripting, and cluster or sentinel setup.
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/opencode
  version: "1.0.0"
  domain: backend
  triggers: Redis, cache, pub/sub, session store, rate limiting, sorted set, streams, Lua script, ioredis, node-redis, redis-client, TTL, cache invalidation, Redis Cluster, Redis Sentinel
  role: specialist
  scope: implementation
  output-format: code
  related-skills: fullstack-guardian, nextjs-developer, nestjs-expert, performance-optimization, database-optimizer
---

# Redis

Redis is an in-memory data structure store used as a cache, message broker, and database. It supports strings, hashes, lists, sets, sorted sets, streams, and more, with built-in replication, persistence, and clustering. It is essential for high-performance caching, real-time messaging, and distributed state management.

## When to Use This Skill

- Implementing caching layers with TTL, cache-aside, and cache invalidation patterns
- Setting up pub/sub for real-time messaging between services or microservices
- Managing user sessions in stateless server environments with Redis as a session store
- Implementing rate limiting with sliding window counters using sorted sets

## Key Capabilities

- Configure Redis clients (ioredis, node-redis) with connection pooling, retry strategies, and TLS for production
- Use sorted sets with `ZREVRANGEBYSCORE` and `ZRANK` for leaderboards, rate limiting, and time-series queries
- Implement pub/sub with `SUBSCRIBE`/`PUBLISH` for cross-service event distribution
- Leverage Redis Streams for message queues with consumer groups, acknowledgments, and persistence

## Best Practices

- Always set TTL on cached data to prevent unbounded memory growth — use `SET key value EX ttl`
- Use connection pooling via ioredis Cluster or Sentinel for high-availability production deployments
- Prefer Redis Streams over pub/sub for reliable message delivery with consumer acknowledgment
- Use `MGET` and pipelining for batch operations instead of sequential `GET` calls to reduce round trips

## Core Workflow

1. **Connect** — Initialize a Redis client with connection URL, retry strategy, and TLS options
2. **Cache** — Implement cache-aside pattern: check cache, return if hit; else query DB, store in cache, return
3. **Invalidate** — Delete or update cache keys when underlying data changes to maintain consistency
4. **Scale** — Move from single instance to Redis Cluster or Sentinel for HA and sharding

## Key Patterns

```typescript
// ioredis client with retry strategy
import Redis from 'ioredis';

const redis = new Redis(process.env.REDIS_URL!, {
  maxRetriesPerRequest: 3,
  retryStrategy: (times) => Math.min(times * 50, 2000),
  enableTLSForSentinelMode: process.env.NODE_ENV === 'production',
  lazyConnect: true,
});

await redis.connect();
```

```typescript
// Cache-aside pattern with typed helper
async function getCachedOrFetch<T>(
  key: string,
  fetch: () => Promise<T>,
  ttl = 300,
): Promise<T> {
  const cached = await redis.get(key);
  if (cached) return JSON.parse(cached) as T;

  const data = await fetch();
  await redis.setex(key, ttl, JSON.stringify(data));
  return data;
}
```

```typescript
// Rate limiter with sorted set (sliding window)
async function checkRateLimit(
  userId: string,
  maxRequests = 100,
  window = 60,
): Promise<boolean> {
  const key = `ratelimit:${userId}`;
  const now = Date.now();
  const windowStart = now - window * 1000;

  // Remove old entries
  await redis.zremrangebyscore(key, 0, windowStart);
  // Count current window
  const count = await redis.zcard(key);

  if (count >= maxRequests) return false;

  await redis.zadd(key, now, `${now}:${Math.random()}`);
  await redis.expire(key, window);
  return true;
}
```

## Constraints

### MUST DO
- Always set TTL for cache keys to prevent unbounded memory growth
- Use `lazyConnect` and explicit `connect()` to handle connection errors gracefully on startup
- Handle Redis connection failures gracefully — your app should degrade (serve stale cache, hit DB) rather than crash

### MUST NOT DO
- Store sensitive data (passwords, tokens, PII) in Redis without encryption
- Use pub/sub for reliable message delivery — use Redis Streams when acknowledgment matters
- Run Redis without persistence (RDB/AOF) in production if data loss is unacceptable
