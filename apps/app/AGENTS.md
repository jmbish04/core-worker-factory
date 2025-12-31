# AGENTS.md - Frontend Application

## Project Overview

The Frontend Application (`apps/app`) is a **Single Page Application (SPA)** built with **React 19** and **Vite**. It relies entirely on client-side rendering (CSR) and does not use Server-Side Rendering (SSR).

## Tech Stack

| Category | Technology | Usage |
|----------|------------|-------|
| **Runtime** | pnpm | Package manager & script runner |
| **Framework** | React 19 | UI Library (Client-side only) |
| **Build Tool** | Vite | pnpmdler & Dev Server |
| **Routing** | TanStack Router | Type-safe file-based routing |
| **Styling** | Tailwind CSS v4 | Utility-first CSS |
| **Components** | shadcn/ui | Reusable UI components |
| **State (Client)** | Jotai | Global client-side state atoms |
| **State (Server)** | TanStack Query | Server state & Auth management |
| **Auth** | Better Auth | Authentication (Cookie-based) |

## Directory Structure

```text
apps/app/
├── src/
│   ├── routes/               # Page components & Route definitions
│   │   ├── (app)/            # Authenticated route group
│   │   ├── (auth)/           # Public authentication route group
│   │   ├── __root.tsx        # Root layout & providers
│   │   └── index.tsx         # Landing page
│   ├── components/           # UI Components
│   │   ├── ui/               # shadcn/ui primitives (Do not edit directly)
│   │   ├── auth/             # Authentication forms & components
│   │   └── layout/           # Global layout components
│   ├── lib/
│   │   ├── auth.ts           # Better Auth client configuration
│   │   ├── client.ts         # RPC/API clients
│   │   └── queries/          # TanStack Query definitions (e.g., session.ts)
│   └── styles/               # Global CSS & Tailwind config
├── index.html                # Entry HTML
└── vite.config.ts            # Configuration

```

## Essential Commands

Run these commands from the root or within `apps/app`:

```bash
# Development
pnpm --filter @repo/app dev    # Start Vite dev server

# Testing & Quality
pnpm --filter @repo/app test   # Run tests (Vitest)
pnpm --filter @repo/app lint   # Lint code

# Build
pnpm --filter @repo/app build  # Build for production

```

## Architecture & Conventions

### 1. Routing (TanStack Router)

* **File-Based Routing:** Routes are defined in `src/routes`.
* **Route Groups:**
* `(app)/`: Contains all **protected** routes requiring authentication.
* `(auth)/`: Contains **public** routes (Login, Signup).
* *Note: Parentheses are used to create logical groups without affecting the URL path.*


* **Layouts:** Use layout components with `<Outlet />` for nested route rendering.
* **Context:**
* Access route context via `Route.useRouteContext()`, **never** via props.
* Always import the specific route definition to ensure type safety:
```tsx
import { Route } from "@/routes/(app)/route";
// ...
const context = Route.useRouteContext();

```




* **Navigation:**
* Use `<Link>` from `@tanstack/react-router` for internal navigation.
* Use `<a>` tags **only** for external links or undefined routes.
* Use `activeProps` on `<Link>` for active state styling.



### 2. Authentication (Better Auth)

**Core Rules:**

* **Provider:** Uses Better Auth with cookie-based sessions (no localStorage/sessionStorage).
* **State Source:** **Never** use Better Auth's `useSession()` hook directly in components. **Always** use the TanStack Query wrappers defined in `lib/queries/session.ts`.
* **Wrappers:** Use `useSessionQuery()` for optional auth or `useSuspenseSessionQuery()` for required auth.
* **Validation:** A valid session requires **both** `session.user` AND `session.session` to exist.

**Implementation Details:**

* **Caching:** Session queries are cached for **30 seconds**.
* **Auto-Refresh:** Sessions auto-refresh on window focus or network reconnect.
* **Invalidation:** Explicitly invalidate the `'session'` query key after Login or Logout actions to ensure UI freshness.
* **Protection:**
* Auth checks happen in the `beforeLoad` hook of the `(app)` route group, not inside component render logic.
* Auth errors (401/403) must trigger redirects via **Error Boundaries** or the router's `redirect` throw.



```typescript
// Example: Protected Route Guard (routes/(app)/route.tsx)
export const Route = createFileRoute('/(app)')({
  beforeLoad: async ({ context }) => {
    const { session } = context.auth;
    if (!session?.user || !session?.session) {
      throw redirect({ to: '/login' });
    }
  },
});

```

### 3. State Management

* **Server State:** Use **TanStack Query**. This includes Authentication, API data, and Async operations.
* **Client State:** Use **Jotai** atoms for global UI state (e.g., sidebar open/close, theme toggles).

### 4. Styling (Tailwind CSS v4)

* Use standard Tailwind utility classes.
* Configuration is handled via CSS variables in `styles/globals.css`.
* Do not create a `tailwind.config.js` unless complex customizations are strictly required; prefer CSS-based configuration.

### 5. Code Quality

* **Strict TypeScript:** No `any` types. Use strict null checks.
* **Path Aliases:** Use `@/*` for all imports (e.g., `import { Button } from "@/components/ui/button"`).
