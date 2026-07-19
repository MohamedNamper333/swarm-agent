---
name: prisma
description: Use when working with Prisma ORM for database schema design, migrations, queries, relations, and type-safe database access in Node.js/TypeScript projects. Invoke for schema modeling, migration management, relation queries, pagination, aggregation, middleware, and optimizing Prisma Client performance.
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/opencode
  version: "1.0.0"
  domain: backend
  triggers: Prisma, ORM, schema, migration, database, PostgreSQL, MySQL, SQLite, MongoDB, Prisma Client, Prisma Studio, datasource, generator, $transaction, raw query
  role: specialist
  scope: implementation
  output-format: code
  related-skills: nextjs-developer, nestjs-expert, developer, fullstack-guardian, postgres-pro
---

# Prisma ORM

Prisma is a next-generation ORM for Node.js and TypeScript that provides a declarative data modeling language, automated migrations, and a type-safe query builder. It replaces traditional ORMs with a schema-driven approach where your database schema is the single source of truth, generating fully typed clients that catch query errors at compile time.

## When to Use This Skill

- Setting up Prisma schema with models, enums, relations, and indexes
- Writing and running database migrations in development and production
- Implementing complex queries with filtering, pagination, sorting, and relations
- Optimizing Prisma Client performance with select, include, batch, and raw queries
- Integrating Prisma into Next.js, NestJS, or Express applications

## Key Capabilities

- Define data models using Prisma Schema Language with relations (1:1, 1:m, m:n), composite keys, and constraints
- Generate and manage database migrations with `prisma migrate dev` and `prisma migrate deploy`
- Execute type-safe CRUD queries, nested writes, transactional operations, and raw SQL
- Configure Prisma Client middleware for logging, soft deletes, and field-level encryption

## Best Practices

- Always use `select` or `include` to fetch only the fields you need and avoid over-fetching
- Use `@datasource` connection pooling with PgBouncer for serverless deployments
- Keep Prisma Client instantiation as a singleton to avoid connection exhaustion in serverless environments
- Write idempotent migrations and always preview them with `prisma migrate dev --create-only` before applying
- Use `$transaction` for operations that require atomicity across multiple queries

## Core Workflow

1. **Model** — Define your schema in `schema.prisma` with proper relations, indexes, and field types
2. **Migrate** — Run `prisma migrate dev` to generate and apply migrations locally
3. **Generate** — Run `prisma generate` to update the type-safe client
4. **Query** — Use the generated Prisma Client in your application code
5. **Optimize** — Profile queries with Prisma Client logs and add indexes where needed

## Key Patterns

```prisma
// Schema — User with posts (1:m) and profile (1:1)
model User {
  id        String   @id @default(cuid())
  email     String   @unique
  name      String?
  posts     Post[]
  profile   Profile?
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
}

model Post {
  id        String   @id @default(cuid())
  title     String
  content   String?
  published Boolean  @default(false)
  author    User     @relation(fields: [authorId], references: [id])
  authorId  String
  createdAt DateTime @default(now())
}

model Profile {
  id     String @id @default(cuid())
  bio    String
  userId String @unique
  user   User   @relation(fields: [userId], references: [id])
}
```

```typescript
// Query — Nested include with pagination and filtering
const userWithPosts = await prisma.user.findUnique({
  where: { email: 'user@example.com' },
  include: {
    posts: {
      where: { published: true },
      orderBy: { createdAt: 'desc' },
      take: 10,
      skip: 0,
    },
    profile: true,
  },
});
```

## Constraints

### MUST DO
- Run `prisma generate` after every schema change before using the client
- Use `@map` and `@@map` for table/column naming conventions when needed
- Add database indexes (`@@index`) on columns used in `where`, `orderBy`, and `unique` constraints
- Use `prisma migrate deploy` in CI/CD for production migrations

### MUST NOT DO
- Commit `.env` files containing database credentials
- Run `prisma migrate dev` in production (use `prisma migrate deploy` instead)
- Use `findMany` without `take` on large tables (always paginate)
- Ignore migration warnings about data loss without reviewing them carefully
