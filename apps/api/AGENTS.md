# AGENTS.md - API Service

## Overview

The API service (`apps/api`) is a Hono-based worker that serves as the backend for the application. It utilizes **tRPC** for type-safe communication with the frontend, **Better Auth** for authentication, and **Drizzle ORM** with **Cloudflare Hyperdrive** to connect to a PostgreSQL database (Neon).

## Directory Structure

```text
apps/api/
├── AGENTS.md                 # This file
├── wrangler.jsonc            # Cloudflare Worker configuration
├── package.json              # Dependencies
├── dev.ts                    # Local development entry point
├── src/
│   ├── index.ts              # Main Worker entry point (Hono)
│   ├── worker.ts             # Cloudflare Worker export
│   ├── trpc.ts               # tRPC init and procedure helpers
│   ├── auth.ts               # Better Auth configuration
│   ├── db/
│   │   ├── index.ts          # Drizzle client instance
│   │   └── schema.ts         # Database schema definitions
│   └── routers/              # tRPC routers
│       ├── index.ts          # Root router
│       ├── auth.ts           # Auth-related procedures
│       └── user.ts           # User-related procedures

```

## Tech Stack & Bindings

| Category | Technology | Usage |
| --- | --- | --- |
| **Runtime** | Bun | Package manager & local runtime |
| **Framework** | Hono | Web standard edge framework |
| **API** | tRPC | Type-safe RPC with Zod validation |
| **Database** | Postgres (Neon) | Primary data store |
| **Connection** | Hyperdrive | Cloudflare connection pooling |
| **ORM** | Drizzle ORM | TypeScript ORM |
| **Auth** | Better Auth | Authentication & Session management |
| **AI** | Vercel AI SDK | LLM integration (`@ai-sdk/openai`) |
| **Email** | Resend | Transactional emails |

### Configuration (`wrangler.jsonc`)

The worker uses **Hyperdrive** for database connections to ensure performance at the edge.

```jsonc
// Env Bindings
{
  "hyperdrive": [
    { "binding": "HYPERDRIVE_CACHED", "id": "..." }, // Read-heavy operations
    { "binding": "HYPERDRIVE_DIRECT", "id": "..." }  // Write-heavy / Transactional
  ],
  "vars": {
    "resend_EMAIL_FROM": "onboarding@resend.dev",
    "APP_ORIGIN": "[https://example.com](https://example.com)"
  }
}

```

## Development Guidelines

### 1. Database Access

* **ALWAYS** use Drizzle ORM. Never write raw SQL strings unless absolutely necessary for complex aggregations.
* **ALWAYS** use the `HYPERDRIVE` binding in production/preview.
* **Schema Changes:** logical changes belong in `@repo/db`. The API consumes the schema from the workspace package.

```typescript
// ✅ Correct Usage
import { db } from '@/db';
import { users } from '@repo/db/schema';
import { eq } from 'drizzle-orm';

const user = await db.select().from(users).where(eq(users.id, input.id));

```

### 2. Authentication (Better Auth)

* The app uses **Better Auth** with the PostgreSQL adapter.
* Auth checks should be done via tRPC middleware `protectedProcedure`.
* Passkeys are supported via `@better-auth/passkey`.

```typescript
// ✅ Protected Route Example
export const userRouter = router({
  me: protectedProcedure.query(async ({ ctx }) => {
    return ctx.user; // User is attached by middleware
  }),
});

```

### 3. tRPC API Design

* **Input Validation:** Always use `zod` schemas for input validation.
* **Error Handling:** Use `TRPCError` with appropriate codes (`NOT_FOUND`, `UNAUTHORIZED`, `BAD_REQUEST`).
* **Procedures:** Group procedures into logical routers (e.g., `user`, `org`, `billing`).

### 4. AI Integration (Vercel AI SDK)

* Use `ai` and `@ai-sdk/openai` for LLM operations.
* Streaming responses should use the Hono stream helper or Vercel AI SDK's `streamText`.

```typescript
import { streamText } from 'ai';
import { openai } from '@ai-sdk/openai';

// Hono Route
app.post('/api/chat', async (c) => {
  const { messages } = await c.req.json();
  const result = await streamText({
    model: openai('gpt-4o'),
    messages,
  });
  return result.toDataStreamResponse();
});

```

## Deployment

* **Command:** `bun deploy` (runs `wrangler deploy`)
* **Environment Variables:** Managed via `.env` locally and Wrangler secrets in production.
* **Pre-deploy:** Ensure `@repo/email` is built and DB migrations (`@repo/db`) are applied.

```

---

### `apps/app/AGENTS.md`

```markdown
# AGENTS.md - Frontend Application

## Overview

The Frontend Application (`apps/app`) is a **React 19** Single Page Application (SPA) built with **Vite** and **TanStack Router**. It uses **shadcn/ui** for the interface and **tRPC** (via TanStack Query) to communicate with the API.

## Directory Structure

```text
apps/app/
├── AGENTS.md                 # This file
├── wrangler.jsonc            # Cloudflare Worker (Assets) config
├── package.json              # Dependencies
├── vite.config.ts            # Vite configuration
├── src/
│   ├── main.tsx              # Entry point
│   ├── App.tsx               # Root component
│   ├── routes/               # TanStack Router file-based routes
│   │   ├── __root.tsx        # Root layout
│   │   ├── (app)/            # Authenticated routes layout
│   │   └── (auth)/           # Public/Auth routes layout
│   ├── components/           # UI Components
│   │   ├── ui/               # shadcn/ui primitives
│   │   └── auth/             # Auth forms & components
│   ├── lib/
│   │   ├── trpc.ts           # tRPC React client
│   │   ├── auth.ts           # Better Auth client
│   │   └── store.ts          # Global state (Jotai)
│   └── hooks/                # Custom React hooks

```

## Tech Stack

| Category | Technology | Usage |
| --- | --- | --- |
| **Framework** | React 19 | UI Library |
| **Build Tool** | Vite | Bundler & Dev Server |
| **Routing** | TanStack Router | Type-safe file-based routing |
| **State** | Jotai | Atomic global state |
| **Data Fetching** | TanStack Query | Async state management (via tRPC) |
| **API Client** | tRPC | Type-safe API calls |
| **Styling** | Tailwind CSS v4 | Utility-first CSS |
| **UI Lib** | shadcn/ui | Radix-based accessible components |

## Development Guidelines

### 1. Routing (TanStack Router)

* Use **File-Based Routing** in `src/routes`.
* Use `__root.tsx` for global providers.
* Use directory groups (e.g., `(app)`, `(auth)`) to organize layouts without affecting URL paths.
* **Link Components:** Always use the type-safe `<Link>` component.

```tsx
// ✅ Correct Usage
import { Link } from '@tanstack/react-router';

<Link to="/dashboard" params={{ id: '123' }} className="...">
  Go to Dashboard
</Link>

```

### 2. Data Fetching (tRPC)

* Use the `trpc` hook for all API interactions.
* **Queries:** Use `trpc.router.procedure.useQuery`.
* **Mutations:** Use `trpc.router.procedure.useMutation` and invalidate queries on success.

```tsx
// ✅ Fetching Data
const { data, isLoading } = trpc.user.me.useQuery();

// ✅ Mutating Data
const utils = trpc.useUtils();
const mutation = trpc.user.update.useMutation({
  onSuccess: () => {
    utils.user.me.invalidate(); // Refresh data
  }
});

```

### 3. State Management (Jotai)

* Use **Jotai** atoms for global client-side state (e.g., theme, sidebar toggle).
* Avoid Redux/Context for simple state; use Atoms.
* Use **TanStack Query** (via tRPC) for ALL server-side state. Do not store server data in Jotai atoms manually.

### 4. UI Components (shadcn/ui)

* Components live in `src/components/ui`.
* Do not modify primitives directly unless updating the design system.
* Compose complex UIs in `src/components/{feature}` using these primitives.
* **Tailwind v4:** Use the new simplified configuration. No `tailwind.config.js` is needed if using CSS-based config.

### 5. Authentication

* Use the exported `authClient` from `src/lib/auth.ts`.
* Protect routes using TanStack Router's `beforeLoad` or a layout wrapper that checks auth state.

```typescript
// src/routes/(app).tsx
export const Route = createFileRoute('/(app)')({
  beforeLoad: async ({ context }) => {
    if (!context.auth.isAuthenticated) {
      throw redirect({ to: '/login' });
    }
  },
});

```

## Deployment

* **Command:** `bun deploy` (runs `wrangler deploy`).
* **Serving:** Deployed as a Cloudflare Worker serving Static Assets (`dist` folder).
* **SPA Handling:** Wrangler is configured with `"not_found_handling": "single-page-application"` to support client-side routing.
