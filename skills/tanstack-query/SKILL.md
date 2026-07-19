---
name: tanstack-query
description: "Manages server state, caching, and data synchronization using TanStack Query (React Query) with TypeScript."
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/Jeffallan
  version: "1.1.0"
  domain: frontend
  triggers: TanStack Query, React Query, useQuery, useMutation, useInfiniteQuery, QueryClient, cache, optimistic update, SSR, stale-while-revalidate
  role: specialist
  scope: implementation
  output-format: code
  related-skills: react-expert, zustand, test-master, fullstack-guardian
---

# TanStack Query

Server state management: queries, mutations, caching, optimistic updates, infinite queries, and SSR with TanStack Query.

## When to Use This Skill

- Synchronizing server state with React/Vue/Svelte/Solid applications
- Replacing manual `useEffect` + `fetch` patterns with declarative data fetching
- Implementing infinite scroll or paginated data loading patterns
- Handling mutations with automatic cache invalidation and optimistic updates
- Prefetching and hydrating data in SSR/SSG frameworks (Next.js, Remix, SvelteKit)

## Key Capabilities

- **Declarative Queries** — Fetch, cache, and refetch data with `useQuery()` including automatic background refetching, stale detection, and garbage collection
- **Mutations & Cache Updates** — Perform create/update/delete operations with `useMutation()` and invalidate related queries or optimistically update the cache
- **Infinite Queries** — Load paginated or cursor-based data with `useInfiniteQuery()` including `fetchNextPage`, `hasNextPage`, and bidirectional loading
- **SSR & Hydration** — Prefetch queries on the server using `prefetchQuery()` and hydrate the cache client-side with `HydrationBoundary` for zero-loading states
- **Query Invalidation & Refetching** — Control cache freshness with `queryClient.invalidateQueries()`, `refetchInterval`, `staleTime`, and `gcTime` (formerly `cacheTime`)
- **Devtools & Debugging** — Inspect query state, cache contents, refetch timestamps, and mutation history with TanStack Query Devtools

## Best Practices

- Configure sensible defaults globally in `QueryClient` (`staleTime: 30_000`, `gcTime: 5 * 60_000`, `retry: 1`) and override per-query only when needed
- Separate query keys into a hierarchy — `['entity']`, `['entity', id]`, `['entity', { filters }]` — for granular invalidation without over-clearing the cache
- Always provide `placeholderData` (e.g., `keepPreviousData`) for pagination to avoid flash-of-loading between page changes
- Use `onMutate` for optimistic updates with a corresponding `onError` rollback that reverts the cache to the previous state
- Prefer SSR prefetching with `dehydrate`/`HydrationBoundary` over client-side waterfalls for pages where initial data is critical to SEO
