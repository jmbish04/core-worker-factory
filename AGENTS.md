# AGENTS.md - CloudForge Repository

## Project Overview

CloudForge is an AI-powered, agentic service that accepts natural language prompts to automatically plan, build, and deploy Cloudflare Workers. The system uses a coordinated team of AI agents powered by Cloudflare Workers AI, orchestrated through the Cloudflare Agents SDK, with secure code execution in Cloudflare Sandbox SDK containers.

## Repository Structure

```
cloudforge/
├── AGENTS.md                      # This file - root agent guidance
├── apps/
│   ├── api/                       # Backend Worker (Hono + Agents SDK)
│   │   ├── AGENTS.md              # API-specific agent guidance
│   │   ├── src/
│   │   │   ├── index.ts           # Main entry point
│   │   │   ├── agents/            # Agent class definitions
│   │   │   ├── routes/            # Hono REST API routes
│   │   │   ├── websocket/         # WebSocket handlers
│   │   │   ├── mcp/               # MCP server implementation
│   │   │   └── lib/               # Utilities
│   │   ├── Dockerfile             # Custom Sandbox SDK image
│   │   └── wrangler.jsonc         # Cloudflare Worker config
│   └── app/                       # Frontend Worker (React + shadcn)
│       ├── AGENTS.md              # Frontend-specific agent guidance
│       ├── src/
│       │   ├── components/        # UI components
│       │   ├── pages/             # Route pages
│       │   ├── hooks/             # Custom React hooks
│       │   ├── contexts/          # React contexts (WebSocket, etc.)
│       │   └── lib/               # Utilities
│       └── wrangler.jsonc         # Cloudflare Worker config
├── packages/
│   ├── db/                        # Drizzle schema & migrations
│   │   ├── src/schema.ts          # Database schema definitions
│   │   ├── drizzle/               # Generated migrations
│   │   └── drizzle.config.ts      # Drizzle configuration
│   └── shared/                    # Shared types & utilities
│       └── src/
│           ├── types.ts           # Shared TypeScript types
│           └── constants.ts       # Shared constants
├── turbo.json                     # Turborepo configuration
├── package.json                   # Root package.json
└── pnpm-workspace.yaml            # PNPM workspace config
```

## Technology Stack

### Core Technologies
| Technology | Purpose | Documentation |
|------------|---------|---------------|
| Cloudflare Workers | Serverless compute | https://developers.cloudflare.com/workers/ |
| Cloudflare Agents SDK | Multi-agent orchestration | https://developers.cloudflare.com/agents/ |
| Cloudflare Sandbox SDK | Secure code execution | https://developers.cloudflare.com/sandbox/ |
| Cloudflare D1 | SQLite database | https://developers.cloudflare.com/d1/ |
| Cloudflare R2 | Object storage | https://developers.cloudflare.com/r2/ |
| Workers AI | LLM inference | https://developers.cloudflare.com/workers-ai/ |
| Hono | Web framework | https://hono.dev/ |
| Drizzle ORM | Database ORM | https://orm.drizzle.team/ |
| React | Frontend framework | https://react.dev/ |
| shadcn/ui | UI components | https://ui.shadcn.com/ |

### Key Patterns
- **Monorepo**: Turborepo with PNPM workspaces
- **API Design**: REST + WebSocket + MCP with OpenAPI 3.1.0
- **Database**: Drizzle ORM with D1 (never raw SQL in application code)
- **State Management**: Durable Objects for agent state
- **Realtime**: WebSocket subscriptions for progress updates

## Agent Architecture

CloudForge uses a multi-agent system where each agent has specific responsibilities:

```
┌─────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR AGENT                        │
│  - Coordinates all other agents                             │
│  - Manages request lifecycle                                │
│  - Generates documentation queries                          │
│  - Tracks overall progress                                  │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│    PLANNER    │ │    BACKEND    │ │      UX       │
│  - Creates    │ │  - Worker     │ │  - React      │
│    build plan │ │    code       │ │    components │
│  - Assigns    │ │  - API impl   │ │  - shadcn UI  │
│    tasks      │ │  - Sandbox    │ │  - Styling    │
└───────────────┘ └───────────────┘ └───────────────┘
        │             │             │
        ▼             ▼             ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│ DATA ENGINEER │ │     API       │ │     QA        │
│  - Drizzle    │ │  - OpenAPI    │ │  - Testing    │
│    schemas    │ │  - Routes     │ │  - Validation │
│  - Migrations │ │  - Zod        │ │  - Build fix  │
└───────────────┘ └───────────────┘ └───────────────┘
                      │
                      ▼
              ┌───────────────┐
              │ DOCUMENTATION │
              │  - README     │
              │  - API docs   │
              │  - Comments   │
              └───────────────┘
```

## Critical Rules for All Agents

### 1. Database Access
```typescript
// ✅ ALWAYS use Drizzle ORM
import { drizzle } from 'drizzle-orm/d1';
import * as schema from '@cloudforge/db/schema';

const db = drizzle(env.DB, { schema });
const users = await db.select().from(schema.users);

// ❌ NEVER use raw SQL in application code
const result = await env.DB.prepare('SELECT * FROM users').all(); // FORBIDDEN
```

### 2. API Design
```typescript
// ✅ ALWAYS include operationId for OpenAPI compliance
const route = createRoute({
  method: 'post',
  path: '/requests',
  operationId: 'createRequest', // REQUIRED
  tags: ['Requests'],
  // ...
});

// ✅ ALWAYS use Zod schemas for validation
const CreateRequestSchema = z.object({
  prompt: z.string().min(10),
}).openapi('CreateRequestInput');
```

### 3. Sandbox SDK Usage
```typescript
// ✅ Version must match npm package
FROM docker.io/cloudflare/sandbox:0.3.3  // Match @cloudflare/sandbox version

// ✅ Use consistent sandbox IDs per request
const sandbox = getSandbox(env.Sandbox, `backend-${requestId}`);

// ✅ Always handle errors
try {
  await sandbox.exec('npm install');
} catch (error) {
  // Log and handle gracefully
}
```

### 4. Agent Communication
```typescript
// ✅ Use Durable Object fetch for inter-agent communication
const plannerId = env.PLANNER.idFromName(requestId);
const planner = env.PLANNER.get(plannerId);
await planner.fetch(new Request('http://internal/create-plan', {
  method: 'POST',
  body: JSON.stringify({ requestId, prompt }),
}));
```

### 5. Realtime Updates
```typescript
// ✅ Always broadcast status changes via WebSocket
import { broadcastUpdate } from '../websocket/handler';

broadcastUpdate({
  type: 'task_update',
  requestId,
  data: { taskId, status: 'IN_PROGRESS' },
  timestamp: new Date().toISOString(),
});
```

### 6. Naming Conventions
| Resource | Convention | Example |
|----------|------------|---------|
| Worker name | kebab-case | `my-todo-api` |
| D1 database | `{worker-name}-db` | `my-todo-api-db` |
| R2 bucket | `{worker-name}-assets` | `my-todo-api-assets` |
| KV namespace | `{worker-name}-cache` | `my-todo-api-cache` |
| GitHub repo | Same as worker name | `my-todo-api` |

## Environment Variables

### Required for All Environments
```bash
# Cloudflare Authentication
CLOUDFLARE_API_TOKEN=           # API token with Workers, D1, R2, KV permissions
CLOUDFLARE_ACCOUNT_ID=          # Your Cloudflare account ID

# GitHub Integration
GITHUB_TOKEN=                   # Personal access token with repo permissions
GITHUB_ORG=                     # GitHub organization for created repos

# Database (for local development)
CLOUDFLARE_D1_DATABASE_ID=      # D1 database ID for Drizzle operations
```

### Optional Configuration
```bash
# Feature Flags
ENABLE_DEBUG_LOGGING=false      # Enable verbose logging
ENABLE_PARALLEL_TASKS=true      # Run independent tasks in parallel

# Rate Limiting
MAX_CONCURRENT_SANDBOXES=10     # Maximum concurrent sandbox containers
MAX_REQUESTS_PER_MINUTE=60      # API rate limit
```

## Common Commands

```bash
# Install dependencies
pnpm install

# Development
pnpm dev                        # Start all services in dev mode
pnpm --filter cloudforge-api dev    # Start API only
pnpm --filter cloudforge-app dev    # Start frontend only

# Database
pnpm --filter @cloudforge/db generate  # Generate Drizzle migrations
pnpm --filter @cloudforge/db push      # Push migrations to D1
pnpm --filter @cloudforge/db studio    # Open Drizzle Studio

# Build
pnpm build                      # Build all packages
pnpm typecheck                  # Run TypeScript type checking
pnpm lint                       # Run ESLint

# Deploy
pnpm --filter cloudforge-api deploy   # Deploy API to Cloudflare
pnpm --filter cloudforge-app deploy   # Deploy frontend to Cloudflare

# Testing
pnpm test                       # Run all tests
pnpm test:e2e                   # Run end-to-end tests
```

## Cloudflare Documentation Queries

When building workers, agents should query Cloudflare documentation for up-to-date information. Common query patterns:

```typescript
// Generate queries based on user prompt
const queries = [
  'Workers AI text generation binding configuration',
  'D1 database Drizzle ORM integration tutorial',
  'Hono framework Cloudflare Workers REST API',
  'Workers WebSocket Durable Objects realtime',
  'R2 storage bucket binding file upload',
];

// Load docs context via MCP
await agent.addMcpServer('cloudflare-docs', 'https://developers.cloudflare.com/mcp');
const docsContext = await agent.callMcpTool('cloudflare-docs', 'search', { query });
```

## Error Handling Guidelines

### API Errors
```typescript
// Use consistent error response format
return c.json({
  error: {
    code: 'VALIDATION_ERROR',
    message: 'Invalid request body',
    details: zodError.errors,
  }
}, 400);
```

### Agent Errors
```typescript
// Log to activity log and broadcast failure
await db.insert(agentActivityLog).values({
  requestId,
  agentName: 'BACKEND',
  action: 'execute_task',
  status: 'ERROR',
  errorDetails: error.message,
});

broadcastUpdate({
  type: 'task_update',
  requestId,
  data: { taskId, status: 'FAILED', error: error.message },
  timestamp: new Date().toISOString(),
});
```

### Sandbox Errors
```typescript
// Always cleanup on error
try {
  await sandbox.exec('npm run build');
} catch (error) {
  // Log the error
  console.error('Sandbox execution failed:', error);
  
  // Attempt to get logs for debugging
  const logs = await sandbox.exec('cat /var/log/build.log').catch(() => null);
  
  // Update task with error details
  await db.update(tasks).set({
    status: 'FAILED',
    agentNotes: `Build failed: ${error.message}\n\nLogs:\n${logs?.stdout || 'No logs available'}`,
  });
}
```

## Security Considerations

1. **Never expose secrets in logs or responses**
2. **Validate all user input with Zod schemas**
3. **Use environment variables for all credentials**
4. **Sandbox all code execution**
5. **Rate limit API endpoints**
6. **Sanitize GitHub URLs before cloning**

## Performance Guidelines

1. **Use streaming for long-running operations**
2. **Cache Cloudflare docs queries in KV**
3. **Batch database operations where possible**
4. **Use shallow git clones (depth=1)**
5. **Clean up sandbox containers after use**

## Contributing

When adding new features:
1. Update the relevant AGENTS.md file
2. Add OpenAPI documentation for new endpoints
3. Include Zod schemas for validation
4. Add WebSocket broadcast for status updates
5. Update the FutureFeatures page if applicable

---

For app-specific guidance, see:
- [apps/api/AGENTS.md](./apps/api/AGENTS.md) - Backend Worker development
- [apps/app/AGENTS.md](./apps/app/AGENTS.md) - Frontend development
```
