---
name: supabase
description: Use when building applications with Supabase for backend services including PostgreSQL database, authentication, realtime subscriptions, storage, and edge functions. Invoke for database schema design, Row Level Security policies, user sign-up/login flows, realtime data sync, file uploads, and serverless edge functions.
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/opencode
  version: "1.0.0"
  domain: backend
  triggers: Supabase, PostgreSQL, RLS, auth, realtime, storage, edge functions, supabase-js, Supabase CLI, database, row level security, authentication, file upload
  role: specialist
  scope: implementation
  output-format: code
  related-skills: prisma, nextjs-developer, fullstack-guardian, secure-code-guardian, postgres-pro
---

# Supabase

Supabase is an open-source Firebase alternative that provides a full suite of backend services built on PostgreSQL. It offers a managed database with realtime capabilities, built-in authentication with multiple providers, file storage with CDN, and serverless edge functions — all accessible through a unified SDK.

## When to Use This Skill

- Setting up a PostgreSQL database with Supabase and writing Row Level Security policies
- Implementing authentication flows (email/password, OAuth, magic link, phone)
- Building realtime features like live cursors, chat, or collaborative editing
- Managing file uploads with Supabase Storage including image transformations and CDN

## Key Capabilities

- Design database schemas using the Supabase SQL editor or migrations, with full PostgreSQL feature support
- Implement Row Level Security (RLS) policies for fine-grained, database-enforced access control
- Subscribe to realtime changes on tables, rows, or broad channels over WebSocket
- Upload, serve, and transform files via Supabase Storage with built-in CDN and image optimization

## Best Practices

- Always enable RLS on every table and write policies that restrict access by `auth.uid()` — never rely on the client alone
- Use the Supabase CLI for local development with `supabase start` and manage schema through migration files
- Keep realtime subscriptions scoped to only the tables and events you need to avoid bandwidth waste
- Store secrets and service role keys in server-only environments — never expose them to the client

## Core Workflow

1. **Schema** — Design tables in the Supabase dashboard or via migration files with the CLI
2. **Secure** — Enable RLS and write row-level policies per table using SQL
3. **Integrate** — Use `supabase-js` in your app to query, subscribe, and manage auth
4. **Ship** — Deploy schema changes with `supabase db push` and manage environments

## Key Patterns

```sql
-- RLS Policy — users can only read their own profile
CREATE POLICY "Users can read own profile"
  ON profiles
  FOR SELECT
  USING (auth.uid() = id);
```

```typescript
// Client — Realtime subscription with auth
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
);

// Subscribe to realtime changes on a table
const channel = supabase
  .channel('room-1')
  .on('postgres_changes',
    { event: 'INSERT', schema: 'public', table: 'messages' },
    (payload) => console.log('New message:', payload.new),
  )
  .subscribe();
```

## Constraints

### MUST DO
- Enable RLS on all tables with user-data and write restrictive policies
- Use the Supabase CLI for local development to avoid breaking production
- Set up proper email templates and redirect URLs for auth flows

### MUST NOT DO
- Use the service_role key on the client side — it bypasses RLS entirely
- Disable RLS on tables that contain user-specific data
- Store sensitive business logic in database functions accessible from the client
