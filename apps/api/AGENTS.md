# AGENTS.md - API Service

## Overview

The API service (`apps/api`) is a Hono-based worker that serves as the backend for the application. It utilizes **tRPC** for type-safe communication with the frontend, **Better Auth** for authentication, and **Drizzle ORM** with **Cloudflare Hyperdrive** to connect to a PostgreSQL database.

**Core Architecture Highlights:**
* **AI Normalization:** Uses the **OpenAI Node.js SDK** as the single standard interface for all AI providers (OpenAI, Google GenAI, Cloudflare Workers AI).
* **Agent System:** Built using the **Cloudflare Agents SDK**, leveraging stateful "batteries-included" Durable Objects for persistent agentic workflows.

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
│   ├── agents/               # Cloudflare Agents SDK implementations
│   │   ├── index.ts          # Agent registry/exports
│   │   └── worker-agent.ts   # Specific agent implementation
│   └── routers/              # tRPC routers
│       ├── index.ts          # Root router
│       ├── auth.ts           # Auth-related procedures
│       └── user.ts           # User-related procedures

```

## Tech Stack & Bindings

| Category | Technology | Usage |
| --- | --- | --- |
| **Runtime** | pnpm | Package manager & local runtime |
| **Framework** | Hono | Web standard edge framework |
| **API** | tRPC | Type-safe RPC with Zod validation |
| **Database** | Postgres (Neon) | Primary data store |
| **Connection** | Hyperdrive | Cloudflare connection pooling |
| **ORM** | Drizzle ORM | TypeScript ORM |
| **Auth** | Better Auth | Authentication & Session management |
| **AI** | **OpenAI Node SDK** | Standardized LLM Client (`openai`) |
| **Agents** | **Cloudflare Agents SDK** | Stateful Durable Object Agents |
| **Email** | Resend | Transactional emails |

## Development Guidelines

### 1. AI Integration (OpenAI SDK Normalization)

**Strict Rule:** Do not use `ai-sdk` (Vercel AI SDK).
We use the official `openai` package to normalize interactions across all providers.

**Configuration Pattern:**
Instantiate the `OpenAI` client dynamically based on the provider required.

```typescript
import OpenAI from 'openai';

// 1. Standard OpenAI
const openai = new OpenAI({ apiKey: env.OPENAI_API_KEY });

// 2. Cloudflare Workers AI (via OpenAI Compatibility)
const workersAi = new OpenAI({
  apiKey: env.CLOUDFLARE_API_TOKEN,
  baseURL: `https://api.cloudflare.com/client/v4/accounts/${env.CLOUDFLARE_ACCOUNT_ID}/ai/v1`,
});

// 3. Usage Example
const completion = await workersAi.chat.completions.create({
  model: '@cf/meta/llama-3-8b-instruct', // Use provider-specific model IDs
  messages: [{ role: 'user', content: 'Hello' }],
});

```

### 2. Cloudflare Agents SDK

Agents are stateful Durable Objects. Use the Cloudflare Agents SDK structure.

* **Stateful:** Agents must persist their context/history in the Durable Object storage.
* **Batteries Included:** Leverage the SDK's built-in handling for state management and connection.

```typescript
import { Agent } from 'cloudflare-agents-sdk'; // Pseudo-code for SDK import

export class BuildAgent extends Agent {
  async onRequest(request: Request) {
    // Agent logic here
  }
}

```

### 3. Database Access

* **ALWAYS** use Drizzle ORM.
* **ALWAYS** use the `HYPERDRIVE` binding in production/preview.

```typescript
// ✅ Correct Usage
import { db } from '@/db';
import { users } from '@repo/db/schema';
import { eq } from 'drizzle-orm';

const user = await db.select().from(users).where(eq(users.id, input.id));

```

### 4. Authentication (Better Auth)

* Use **Better Auth** with the PostgreSQL adapter.
* Auth checks via tRPC middleware `protectedProcedure`.

```typescript
// ✅ Protected Route Example
export const userRouter = router({
  me: protectedProcedure.query(async ({ ctx }) => {
    return ctx.user;
  }),
});

```

## Deployment

* **Command:** `pnpm deploy` (runs `wrangler deploy`)
* **Environment Variables:** Managed via `.env` locally and Wrangler secrets in production.

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
| **Build Tool** | Vite | pnpmdler & Dev Server |
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
* **Queries:** `trpc.router.procedure.useQuery`
* **Mutations:** `trpc.router.procedure.useMutation`

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

### 3. State Management

* **Jotai:** For client-side UI state (theme, sidebar).
* **TanStack Query:** For all server-side data. Do not duplicate server data into Jotai.

### 4. UI Components (shadcn/ui)

* Components live in `src/components/ui`.
* **Tailwind v4:** Use the new simplified configuration.

### 5. Authentication

* Use the exported `authClient` from `src/lib/auth.ts`.
* Protect routes using TanStack Router's `beforeLoad`.

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

* **Command:** `pnpm deploy` (runs `wrangler deploy`).
* **Serving:** Deployed as a Cloudflare Worker serving Static Assets.
