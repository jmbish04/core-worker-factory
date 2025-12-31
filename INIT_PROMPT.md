# PROJECT: CloudForge - Agentic Cloudflare Worker Builder Service

## OVERVIEW

Build "CloudForge" - an AI-powered, agentic service that accepts natural language prompts (and optional GitHub repo URLs) to automatically plan, build, and deploy Cloudflare Workers. The service uses a coordinated team of AI agents powered by Cloudflare Workers AI, orchestrated through the Cloudflare Agents SDK, with code execution in Cloudflare Sandbox SDK containers.

## ARCHITECTURE SUMMARY

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           CloudForge Platform                            │
├─────────────────────────────────────────────────────────────────────────┤
│  apps/app (Frontend Worker)          │  apps/api (Backend Worker)        │
│  ├── React + shadcn/ui               │  ├── Hono REST API                │
│  ├── Agent Configuration UI          │  ├── WebSocket API (realtime)     │
│  ├── Request/Backlog Viewer          │  ├── MCP Server                   │
│  ├── Worker Management               │  ├── OpenAPI 3.1.0 (/swagger)     │
│  └── Realtime Progress Updates       │  └── Agentic Team Orchestration   │
├─────────────────────────────────────────────────────────────────────────┤
│                         Agentic Team (Durable Objects)                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐   │
│  │ Orchestrator │ │   Planner    │ │   Backend    │ │      UX      │   │
│  │    Agent     │ │    Agent     │ │    Agent     │ │    Agent     │   │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘   │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐   │
│  │Data Engineer │ │     API      │ │Documentation │ │     QA       │   │
│  │    Agent     │ │    Agent     │ │    Agent     │ │    Agent     │   │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘   │
├─────────────────────────────────────────────────────────────────────────┤
│                         Infrastructure                                   │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐   │
│  │  Sandbox SDK │ │      D1      │ │      R2      │ │  Workers AI  │   │
│  │  (Containers)│ │  (Database)  │ │   (Storage)  │ │   (LLMs)     │   │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

## PHASE 1: PROJECT SETUP

### 1.1 Fork and Clone Starter Kit

```bash
# Fork https://github.com/jmbish04/core-react-starter-kit
# The monorepo structure should be:
cloudforge/
├── apps/
│   ├── api/                    # Backend Worker (Hono + Agents SDK)
│   │   ├── src/
│   │   │   ├── index.ts        # Main entry point
│   │   │   ├── agents/         # Agent definitions
│   │   │   ├── routes/         # Hono routes
│   │   │   ├── websocket/      # WebSocket handlers
│   │   │   ├── mcp/            # MCP server implementation
│   │   │   └── db/             # Drizzle schema & migrations
│   │   ├── drizzle/            # Migration files
│   │   ├── Dockerfile          # Custom Sandbox image
│   │   └── wrangler.jsonc
│   └── app/                    # Frontend Worker (React + shadcn)
│       ├── src/
│       │   ├── components/     # UI components
│       │   ├── pages/          # Route pages
│       │   ├── hooks/          # Custom hooks
│       │   └── lib/            # Utilities
│       └── wrangler.jsonc
├── packages/
│   ├── shared/                 # Shared types & utilities
│   └── db/                     # Drizzle schema package
├── turbo.json
└── package.json
```

### 1.2 Custom Dockerfile for Sandbox SDK

Create `apps/api/Dockerfile`:

```dockerfile
# MUST match @cloudflare/sandbox npm package version
FROM docker.io/cloudflare/sandbox:0.3.3

# System dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    jq \
    gh \
    && rm -rf /var/lib/apt/lists/*

# Python packages for GitHub API and Cloudflare API automation
RUN pip install --no-cache-dir \
    cloudflare \
    PyGithub \
    gitpython \
    requests \
    pyyaml \
    toml \
    python-dotenv

# Node.js global packages
RUN npm install -g \
    wrangler \
    @cloudflare/workers-types \
    drizzle-kit \
    typescript \
    tsx

# Pre-configure git
RUN git config --global user.email "cloudforge@workers.dev" && \
    git config --global user.name "CloudForge Bot"

# Create workspace directory
WORKDIR /workspace
```

## PHASE 2: DATABASE SCHEMA (Drizzle + D1)

### 2.1 Drizzle Schema Definition

Create `packages/db/src/schema.ts`:

```typescript
import { sqliteTable, text, integer, real } from 'drizzle-orm/sqlite-core';
import { relations } from 'drizzle-orm';
import { createId } from '@paralleldrive/cuid2';

// ============== REQUESTS ==============
export const requests = sqliteTable('requests', {
  id: text('id').primaryKey().$defaultFn(() => createId()),
  prompt: text('prompt').notNull(),
  githubRepoUrls: text('github_repo_urls'), // JSON array
  status: text('status', { 
    enum: ['PENDING', 'PLANNING', 'IN_PROGRESS', 'REVIEW', 'DEPLOYING', 'COMPLETED', 'FAILED'] 
  }).default('PENDING').notNull(),
  workerName: text('worker_name'),
  workerUrl: text('worker_url'),
  githubRepoCreated: text('github_repo_created'),
  errorMessage: text('error_message'),
  metadata: text('metadata'), // JSON object
  createdAt: integer('created_at', { mode: 'timestamp' }).$defaultFn(() => new Date()),
  updatedAt: integer('updated_at', { mode: 'timestamp' }).$defaultFn(() => new Date()),
});

// ============== ITERATIONS ==============
export const iterations = sqliteTable('iterations', {
  id: text('id').primaryKey().$defaultFn(() => createId()),
  requestId: text('request_id').notNull().references(() => requests.id),
  iterationNumber: integer('iteration_number').notNull().default(1),
  status: text('status', { 
    enum: ['PLANNING', 'EXECUTING', 'REVIEWING', 'COMPLETED', 'FAILED'] 
  }).default('PLANNING').notNull(),
  summary: text('summary'),
  startedAt: integer('started_at', { mode: 'timestamp' }).$defaultFn(() => new Date()),
  completedAt: integer('completed_at', { mode: 'timestamp' }),
});

// ============== PLANS ==============
export const plans = sqliteTable('plans', {
  id: text('id').primaryKey().$defaultFn(() => createId()),
  iterationId: text('iteration_id').notNull().references(() => iterations.id),
  planJson: text('plan_json').notNull(), // Full plan as JSON
  docsQueriesGenerated: text('docs_queries_generated'), // JSON array of CF docs queries
  docsContextLoaded: text('docs_context_loaded'), // JSON object of loaded docs
  createdAt: integer('created_at', { mode: 'timestamp' }).$defaultFn(() => new Date()),
});

// ============== TASKS (Backlog Items) ==============
export const tasks = sqliteTable('tasks', {
  id: text('id').primaryKey().$defaultFn(() => createId()),
  planId: text('plan_id').notNull().references(() => plans.id),
  title: text('title').notNull(),
  description: text('description'),
  assignedAgent: text('assigned_agent', {
    enum: ['ORCHESTRATOR', 'PLANNER', 'BACKEND', 'UX', 'DATA_ENGINEER', 'API', 'DOCUMENTATION', 'QA']
  }).notNull(),
  status: text('status', {
    enum: ['TODO', 'IN_PROGRESS', 'PENDING_PEER_REVIEW', 'IN_REVIEW', 'BLOCKED', 'COMPLETED', 'FAILED']
  }).default('TODO').notNull(),
  priority: integer('priority').default(0),
  parentTaskId: text('parent_task_id'),
  dependencies: text('dependencies'), // JSON array of task IDs
  outputArtifacts: text('output_artifacts'), // JSON array of file paths or URLs
  agentNotes: text('agent_notes'), // Agent reasoning/notes
  reviewNotes: text('review_notes'),
  estimatedComplexity: text('estimated_complexity', { enum: ['LOW', 'MEDIUM', 'HIGH'] }),
  startedAt: integer('started_at', { mode: 'timestamp' }),
  completedAt: integer('completed_at', { mode: 'timestamp' }),
  createdAt: integer('created_at', { mode: 'timestamp' }).$defaultFn(() => new Date()),
});

// ============== AGENT ACTIVITY LOG ==============
export const agentActivityLog = sqliteTable('agent_activity_log', {
  id: text('id').primaryKey().$defaultFn(() => createId()),
  requestId: text('request_id').notNull().references(() => requests.id),
  taskId: text('task_id').references(() => tasks.id),
  agentName: text('agent_name').notNull(),
  action: text('action').notNull(),
  input: text('input'), // JSON
  output: text('output'), // JSON
  tokensUsed: integer('tokens_used'),
  durationMs: integer('duration_ms'),
  status: text('status', { enum: ['SUCCESS', 'ERROR', 'PENDING'] }).default('PENDING'),
  errorDetails: text('error_details'),
  timestamp: integer('timestamp', { mode: 'timestamp' }).$defaultFn(() => new Date()),
});

// ============== WORKERS REGISTRY ==============
export const workersRegistry = sqliteTable('workers_registry', {
  id: text('id').primaryKey().$defaultFn(() => createId()),
  requestId: text('request_id').references(() => requests.id),
  workerName: text('worker_name').notNull().unique(),
  workerUrl: text('worker_url'),
  githubRepoUrl: text('github_repo_url'),
  githubRepoOwner: text('github_repo_owner'),
  githubRepoName: text('github_repo_name'),
  bindingsCreated: text('bindings_created'), // JSON array of binding names
  lastDeployStatus: text('last_deploy_status'),
  lastDeployAt: integer('last_deploy_at', { mode: 'timestamp' }),
  lastBuildLogs: text('last_build_logs'),
  createdAt: integer('created_at', { mode: 'timestamp' }).$defaultFn(() => new Date()),
  updatedAt: integer('updated_at', { mode: 'timestamp' }).$defaultFn(() => new Date()),
});

// ============== AGENT CONFIGURATIONS ==============
export const agentConfigurations = sqliteTable('agent_configurations', {
  id: text('id').primaryKey().$defaultFn(() => createId()),
  agentName: text('agent_name', {
    enum: ['ORCHESTRATOR', 'PLANNER', 'BACKEND', 'UX', 'DATA_ENGINEER', 'API', 'DOCUMENTATION', 'QA']
  }).notNull().unique(),
  systemPrompt: text('system_prompt').notNull(),
  modelId: text('model_id').default('@cf/meta/llama-3.1-70b-instruct'),
  temperature: real('temperature').default(0.7),
  maxTokens: integer('max_tokens').default(4096),
  mcpServersConfig: text('mcp_servers_config'), // JSON array of MCP server URLs
  toolsEnabled: text('tools_enabled'), // JSON array of tool names
  constraints: text('constraints'), // JSON object of agent-specific constraints
  updatedAt: integer('updated_at', { mode: 'timestamp' }).$defaultFn(() => new Date()),
});

// ============== RELATIONS ==============
export const requestsRelations = relations(requests, ({ many }) => ({
  iterations: many(iterations),
  activityLogs: many(agentActivityLog),
  workers: many(workersRegistry),
}));

export const iterationsRelations = relations(iterations, ({ one, many }) => ({
  request: one(requests, { fields: [iterations.requestId], references: [requests.id] }),
  plans: many(plans),
}));

export const plansRelations = relations(plans, ({ one, many }) => ({
  iteration: one(iterations, { fields: [plans.iterationId], references: [iterations.id] }),
  tasks: many(tasks),
}));

export const tasksRelations = relations(tasks, ({ one }) => ({
  plan: one(plans, { fields: [tasks.planId], references: [plans.id] }),
  parentTask: one(tasks, { fields: [tasks.parentTaskId], references: [tasks.id] }),
}));
```

### 2.2 Drizzle Configuration

Create `packages/db/drizzle.config.ts`:

```typescript
import type { Config } from 'drizzle-kit';

export default {
  schema: './src/schema.ts',
  out: './drizzle',
  dialect: 'sqlite',
  driver: 'd1-http',
  dbCredentials: {
    accountId: process.env.CLOUDFLARE_ACCOUNT_ID!,
    databaseId: process.env.CLOUDFLARE_D1_DATABASE_ID!,
    token: process.env.CLOUDFLARE_API_TOKEN!,
  },
} satisfies Config;
```

## PHASE 3: BACKEND WORKER (apps/api)

### 3.1 Wrangler Configuration

Already configured for you .. do not modify the bindings as they have already been created and filled in for you, `apps/api/wrangler.jsonc`:

```jsonc
{
  "$schema": "node_modules/wrangler/config-schema.json",
  "name": "core-worker-factory-api",
  "main": "worker.ts",
  "compatibility_date": "2025-08-15",
  "compatibility_flags": ["nodejs_compat"],

  // [OBSERVABILITY]
  "observability": {
    "enabled": true,
    "head_sampling_rate": 1
  },

  // [BUILD]
  "upload_source_maps": true,

  // [WORKER AI]
  // Usage: env.AI.run
  "ai": {
    "binding": "AI"
  },

  // [CONTAINERS]
  // Sandbox SDK configuration with custom Dockerfile
  "containers": {
    "image": "./Dockerfile",
    "class_name": "SandboxContainer"
  },

  // [DURABLE OBJECTS]
  // Stateful agents managed by Cloudflare Agents SDK
  "durable_objects": {
    "bindings": [
      { "name": "ORCHESTRATOR", "class_name": "OrchestratorAgent" },
      { "name": "ANALYST", "class_name": "AnalystAgent" },
      { "name": "DATA_EXPERT", "class_name": "DataExpertAgent" },
      { "name": "INSIGHTS", "class_name": "InsightsAgent" },
      { "name": "TERMINAL", "class_name": "TerminalAgent" },
      { "name": "SANDBOX", "class_name": "SandboxAgent" }
    ]
  },

  // [MIGRATIONS]
  // Enable SQLite for Durable Objects (Cloudflare Agents SDK requirement)
  "migrations": [
    {
      "tag": "v1",
      "new_sqlite_classes": [
        "OrchestratorAgent",
        "AnalystAgent",
        "DataExpertAgent",
        "InsightsAgent",
        "TerminalAgent",
        "SandboxAgent"
      ]
    }
  ],

  // [STORAGE - KV]
  "kv_namespaces": [
    {
      "binding": "KV",
      "id": "5b7617cc077c45feac0ac856c2ccad34",
      "preview_id": "8d4c9a09b6f642a5b8230e8cf68d6b63"
    }
  ],

  // [STORAGE - D1]
  "d1_databases": [
    {
      "binding": "DB",
      "database_name": "core-worker-factory",
      "database_id": "2f036faf-521c-49cc-8f42-43e18370d821",
      "preview_database_id": "9af6da1f-246c-47c3-b8e1-0489187ffaa2",
      "migrations_dir": "./drizzle/migrations"
    }
  ],

  // [VARS]
  "vars": {
  }
}

```

### 3.2 Main Entry Point with Hono

Create `apps/api/src/index.ts`:

```typescript
import { Hono } from 'hono';
import { cors } from 'hono/cors';
import { logger } from 'hono/logger';
import { prettyJSON } from 'hono/pretty-json';
import { swaggerUI } from '@hono/swagger-ui';
import { OpenAPIHono } from '@hono/zod-openapi';
import { drizzle } from 'drizzle-orm/d1';
import { upgradeWebSocket } from 'hono/cloudflare-workers';
import * as schema from '@cloudforge/db/schema';

// Import routes
import { requestsRoutes } from './routes/requests';
import { workersRoutes } from './routes/workers';
import { agentsRoutes } from './routes/agents';
import { progressRoutes } from './routes/progress';
import { mcpRoutes } from './routes/mcp';
import { websocketHandler } from './websocket/handler';

// Import Agent classes
import { OrchestratorAgent } from './agents/orchestrator';
import { PlannerAgent } from './agents/planner';
import { BackendAgent } from './agents/backend';
import { UXAgent } from './agents/ux';
import { DataEngineerAgent } from './agents/data-engineer';
import { APIAgent } from './agents/api';
import { DocumentationAgent } from './agents/documentation';
import { QAAgent } from './agents/qa';

// Export Sandbox and all Agent classes
export { Sandbox } from '@cloudflare/sandbox';
export { 
  OrchestratorAgent, 
  PlannerAgent, 
  BackendAgent, 
  UXAgent, 
  DataEngineerAgent, 
  APIAgent, 
  DocumentationAgent, 
  QAAgent 
};

// Type definitions
interface Env {
  DB: D1Database;
  ARTIFACTS: R2Bucket;
  CACHE: KVNamespace;
  AI: Ai;
  Sandbox: DurableObjectNamespace;
  ORCHESTRATOR: DurableObjectNamespace;
  PLANNER: DurableObjectNamespace;
  BACKEND: DurableObjectNamespace;
  UX: DurableObjectNamespace;
  DATA_ENGINEER: DurableObjectNamespace;
  API: DurableObjectNamespace;
  DOCUMENTATION: DurableObjectNamespace;
  QA: DurableObjectNamespace;
  CLOUDFLARE_API_TOKEN: string;
  CLOUDFLARE_ACCOUNT_ID: string;
  GITHUB_TOKEN: string;
  GITHUB_ORG: string;
}

// Create OpenAPI-enabled Hono app
const app = new OpenAPIHono<{ Bindings: Env }>();

// Middleware
app.use('*', cors());
app.use('*', logger());
app.use('*', prettyJSON());

// Inject Drizzle DB into context
app.use('*', async (c, next) => {
  const db = drizzle(c.env.DB, { schema });
  c.set('db', db);
  await next();
});

// Mount routes
app.route('/api/v1/requests', requestsRoutes);
app.route('/api/v1/workers', workersRoutes);
app.route('/api/v1/agents', agentsRoutes);
app.route('/api/v1/progress', progressRoutes);
app.route('/mcp', mcpRoutes);

// WebSocket endpoint for realtime updates
app.get('/ws', upgradeWebSocket((c) => websocketHandler(c)));

// OpenAPI Documentation endpoints
app.doc('/openapi.json', {
  openapi: '3.1.0',
  info: {
    title: 'CloudForge API',
    version: '1.0.0',
    description: 'Agentic Cloudflare Worker Builder Service API',
  },
  servers: [
    { url: 'https://cloudforge-api.workers.dev', description: 'Production' },
    { url: 'http://localhost:8787', description: 'Development' },
  ],
});

// Serve OpenAPI as YAML
app.get('/openapi.yaml', async (c) => {
  const spec = app.getOpenAPIDocument({
    openapi: '3.1.0',
    info: { title: 'CloudForge API', version: '1.0.0' },
  });
  const yaml = await import('yaml').then(m => m.stringify(spec));
  return c.text(yaml, 200, { 'Content-Type': 'application/yaml' });
});

// Swagger UI
app.get('/swagger', swaggerUI({ url: '/openapi.json' }));

// Health check
app.get('/health', (c) => c.json({ status: 'healthy', timestamp: new Date().toISOString() }));

export default app;
```

### 3.3 Request Routes with Zod OpenAPI

Create `apps/api/src/routes/requests.ts`:

```typescript
import { OpenAPIHono, createRoute, z } from '@hono/zod-openapi';
import { eq, desc } from 'drizzle-orm';
import { requests, iterations, plans, tasks } from '@cloudforge/db/schema';

const app = new OpenAPIHono();

// Schemas
const CreateRequestSchema = z.object({
  prompt: z.string().min(10).describe('Natural language description of the worker to build'),
  githubRepoUrls: z.array(z.string().url()).optional().describe('Optional GitHub repos to reference'),
  workerName: z.string().regex(/^[a-z0-9-]+$/).optional().describe('Optional worker name (auto-generated if not provided)'),
}).openapi('CreateRequestInput');

const RequestResponseSchema = z.object({
  id: z.string(),
  prompt: z.string(),
  status: z.enum(['PENDING', 'PLANNING', 'IN_PROGRESS', 'REVIEW', 'DEPLOYING', 'COMPLETED', 'FAILED']),
  workerName: z.string().nullable(),
  workerUrl: z.string().nullable(),
  githubRepoCreated: z.string().nullable(),
  createdAt: z.string(),
  updatedAt: z.string(),
}).openapi('RequestResponse');

// Create new worker request
const createRequestRoute = createRoute({
  method: 'post',
  path: '/',
  operationId: 'createRequest',
  tags: ['Requests'],
  summary: 'Create a new worker build request',
  description: 'Submit a natural language prompt to build a new Cloudflare Worker',
  request: {
    body: {
      content: {
        'application/json': { schema: CreateRequestSchema },
      },
    },
  },
  responses: {
    201: {
      description: 'Request created successfully',
      content: {
        'application/json': { schema: RequestResponseSchema },
      },
    },
    400: { description: 'Invalid request' },
  },
});

app.openapi(createRequestRoute, async (c) => {
  const db = c.get('db');
  const body = c.req.valid('json');
  
  // Generate worker name if not provided
  const workerName = body.workerName || `worker-${Date.now().toString(36)}`;
  
  // Insert request
  const [newRequest] = await db.insert(requests).values({
    prompt: body.prompt,
    githubRepoUrls: body.githubRepoUrls ? JSON.stringify(body.githubRepoUrls) : null,
    workerName,
    status: 'PENDING',
  }).returning();
  
  // Trigger orchestrator agent asynchronously
  const orchestratorId = c.env.ORCHESTRATOR.idFromName(newRequest.id);
  const orchestrator = c.env.ORCHESTRATOR.get(orchestratorId);
  await orchestrator.fetch(new Request('http://internal/start', {
    method: 'POST',
    body: JSON.stringify({ requestId: newRequest.id }),
  }));
  
  return c.json(newRequest, 201);
});

// List requests with pagination
const listRequestsRoute = createRoute({
  method: 'get',
  path: '/',
  operationId: 'listRequests',
  tags: ['Requests'],
  summary: 'List all worker build requests',
  request: {
    query: z.object({
      page: z.coerce.number().min(1).default(1),
      limit: z.coerce.number().min(1).max(100).default(20),
      status: z.enum(['PENDING', 'PLANNING', 'IN_PROGRESS', 'REVIEW', 'DEPLOYING', 'COMPLETED', 'FAILED']).optional(),
    }),
  },
  responses: {
    200: {
      description: 'List of requests',
      content: {
        'application/json': {
          schema: z.object({
            data: z.array(RequestResponseSchema),
            pagination: z.object({
              page: z.number(),
              limit: z.number(),
              total: z.number(),
            }),
          }),
        },
      },
    },
  },
});

app.openapi(listRequestsRoute, async (c) => {
  const db = c.get('db');
  const { page, limit, status } = c.req.valid('query');
  
  let query = db.select().from(requests).orderBy(desc(requests.createdAt));
  
  if (status) {
    query = query.where(eq(requests.status, status));
  }
  
  const offset = (page - 1) * limit;
  const results = await query.limit(limit).offset(offset);
  const [{ count }] = await db.select({ count: sql`count(*)` }).from(requests);
  
  return c.json({
    data: results,
    pagination: { page, limit, total: Number(count) },
  });
});

// Get request details with iterations, plans, and tasks
const getRequestRoute = createRoute({
  method: 'get',
  path: '/:id',
  operationId: 'getRequest',
  tags: ['Requests'],
  summary: 'Get request details with full backlog',
  request: {
    params: z.object({ id: z.string() }),
  },
  responses: {
    200: { description: 'Request details' },
    404: { description: 'Request not found' },
  },
});

app.openapi(getRequestRoute, async (c) => {
  const db = c.get('db');
  const { id } = c.req.valid('param');
  
  const request = await db.query.requests.findFirst({
    where: eq(requests.id, id),
    with: {
      iterations: {
        with: {
          plans: {
            with: {
              tasks: true,
            },
          },
        },
      },
    },
  });
  
  if (!request) {
    return c.json({ error: 'Request not found' }, 404);
  }
  
  return c.json(request);
});

// Modify existing worker
const modifyWorkerRoute = createRoute({
  method: 'post',
  path: '/:id/modify',
  operationId: 'modifyWorker',
  tags: ['Requests'],
  summary: 'Submit modification request for existing worker',
  request: {
    params: z.object({ id: z.string() }),
    body: {
      content: {
        'application/json': {
          schema: z.object({
            prompt: z.string().describe('Description of modifications to make'),
          }),
        },
      },
    },
  },
  responses: {
    201: { description: 'Modification request created' },
    404: { description: 'Worker not found' },
  },
});

app.openapi(modifyWorkerRoute, async (c) => {
  // Implementation for modifying existing worker
  const db = c.get('db');
  const { id } = c.req.valid('param');
  const { prompt } = c.req.valid('json');
  
  // Create new iteration for existing request
  const [iteration] = await db.insert(iterations).values({
    requestId: id,
    status: 'PLANNING',
  }).returning();
  
  // Trigger orchestrator for modification
  const orchestratorId = c.env.ORCHESTRATOR.idFromName(id);
  const orchestrator = c.env.ORCHESTRATOR.get(orchestratorId);
  await orchestrator.fetch(new Request('http://internal/modify', {
    method: 'POST',
    body: JSON.stringify({ requestId: id, iterationId: iteration.id, prompt }),
  }));
  
  return c.json({ iterationId: iteration.id }, 201);
});

export { app as requestsRoutes };
```

### 3.4 WebSocket Handler for Realtime Updates

Create `apps/api/src/websocket/handler.ts`:

```typescript
import type { Context } from 'hono';

interface WebSocketMessage {
  type: 'subscribe' | 'unsubscribe' | 'ping';
  requestId?: string;
  channel?: 'request' | 'task' | 'agent';
}

interface BroadcastMessage {
  type: 'task_update' | 'request_update' | 'agent_activity' | 'plan_created';
  requestId: string;
  data: any;
  timestamp: string;
}

// Store active connections by request ID
const subscriptions = new Map<string, Set<WebSocket>>();

export function websocketHandler(c: Context) {
  return {
    onOpen(event: Event, ws: WebSocket) {
      console.log('WebSocket connection opened');
    },
    
    onMessage(event: MessageEvent, ws: WebSocket) {
      try {
        const message: WebSocketMessage = JSON.parse(event.data as string);
        
        switch (message.type) {
          case 'subscribe':
            if (message.requestId) {
              if (!subscriptions.has(message.requestId)) {
                subscriptions.set(message.requestId, new Set());
              }
              subscriptions.get(message.requestId)!.add(ws);
              ws.send(JSON.stringify({
                type: 'subscribed',
                requestId: message.requestId,
              }));
            }
            break;
            
          case 'unsubscribe':
            if (message.requestId) {
              subscriptions.get(message.requestId)?.delete(ws);
            }
            break;
            
          case 'ping':
            ws.send(JSON.stringify({ type: 'pong' }));
            break;
        }
      } catch (error) {
        console.error('WebSocket message error:', error);
      }
    },
    
    onClose(event: CloseEvent, ws: WebSocket) {
      // Remove from all subscriptions
      for (const [requestId, sockets] of subscriptions) {
        sockets.delete(ws);
        if (sockets.size === 0) {
          subscriptions.delete(requestId);
        }
      }
    },
    
    onError(event: Event, ws: WebSocket) {
      console.error('WebSocket error:', event);
    },
  };
}

// Utility function to broadcast updates to subscribed clients
export function broadcastUpdate(message: BroadcastMessage) {
  const sockets = subscriptions.get(message.requestId);
  if (sockets) {
    const payload = JSON.stringify(message);
    for (const ws of sockets) {
      try {
        ws.send(payload);
      } catch (error) {
        console.error('Failed to send to WebSocket:', error);
        sockets.delete(ws);
      }
    }
  }
}

// Export for use in agents
export { subscriptions };
```

### 3.5 MCP Server Implementation

Create `apps/api/src/routes/mcp.ts`:

```typescript
import { McpAgent } from 'agents/mcp';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp';
import { z } from 'zod';
import { drizzle } from 'drizzle-orm/d1';
import * as schema from '@cloudforge/db/schema';

export class CloudForgeMCPServer extends McpAgent {
  server = new McpServer({
    name: 'CloudForge',
    version: '1.0.0',
  });

  async init() {
    // Tool: Create new worker from prompt
    this.server.tool(
      'create_worker',
      'Create a new Cloudflare Worker from a natural language description',
      {
        prompt: z.string().describe('Natural language description of the worker to build'),
        workerName: z.string().optional().describe('Optional worker name'),
        githubRepoUrls: z.array(z.string()).optional().describe('Optional GitHub repos to reference'),
      },
      async ({ prompt, workerName, githubRepoUrls }) => {
        const db = drizzle(this.env.DB, { schema });
        
        const [request] = await db.insert(schema.requests).values({
          prompt,
          workerName: workerName || `worker-${Date.now().toString(36)}`,
          githubRepoUrls: githubRepoUrls ? JSON.stringify(githubRepoUrls) : null,
          status: 'PENDING',
        }).returning();
        
        // Trigger orchestrator
        const orchestratorId = this.env.ORCHESTRATOR.idFromName(request.id);
        const orchestrator = this.env.ORCHESTRATOR.get(orchestratorId);
        await orchestrator.fetch(new Request('http://internal/start', {
          method: 'POST',
          body: JSON.stringify({ requestId: request.id }),
        }));
        
        return {
          content: [{
            type: 'text',
            text: `Worker build request created with ID: ${request.id}. You can track progress at /api/v1/requests/${request.id}`,
          }],
        };
      }
    );

    // Tool: Modify existing worker
    this.server.tool(
      'modify_worker',
      'Submit a modification request for an existing worker',
      {
        workerName: z.string().describe('Name of the worker to modify'),
        prompt: z.string().describe('Description of modifications to make'),
      },
      async ({ workerName, prompt }) => {
        const db = drizzle(this.env.DB, { schema });
        
        const worker = await db.query.workersRegistry.findFirst({
          where: eq(schema.workersRegistry.workerName, workerName),
        });
        
        if (!worker || !worker.requestId) {
          return {
            content: [{
              type: 'text',
              text: `Worker "${workerName}" not found in registry.`,
            }],
            isError: true,
          };
        }
        
        // Create modification iteration
        const [iteration] = await db.insert(schema.iterations).values({
          requestId: worker.requestId,
          status: 'PLANNING',
        }).returning();
        
        return {
          content: [{
            type: 'text',
            text: `Modification request created. Iteration ID: ${iteration.id}`,
          }],
        };
      }
    );

    // Tool: List workers
    this.server.tool(
      'list_workers',
      'List all workers created by CloudForge',
      {
        status: z.enum(['all', 'active', 'failed']).optional().default('all'),
      },
      async ({ status }) => {
        const db = drizzle(this.env.DB, { schema });
        const workers = await db.select().from(schema.workersRegistry);
        
        return {
          content: [{
            type: 'text',
            text: JSON.stringify(workers, null, 2),
          }],
        };
      }
    );

    // Tool: Get request progress
    this.server.tool(
      'get_request_progress',
      'Get the current progress of a worker build request',
      {
        requestId: z.string().describe('ID of the request to check'),
      },
      async ({ requestId }) => {
        const db = drizzle(this.env.DB, { schema });
        
        const request = await db.query.requests.findFirst({
          where: eq(schema.requests.id, requestId),
          with: {
            iterations: {
              with: {
                plans: {
                  with: {
                    tasks: true,
                  },
                },
              },
            },
          },
        });
        
        if (!request) {
          return {
            content: [{ type: 'text', text: 'Request not found' }],
            isError: true,
          };
        }
        
        return {
          content: [{
            type: 'text',
            text: JSON.stringify(request, null, 2),
          }],
        };
      }
    );

    // Tool: Search requests
    this.server.tool(
      'search_requests',
      'Search previous worker build requests',
      {
        query: z.string().describe('Search query'),
        status: z.enum(['PENDING', 'PLANNING', 'IN_PROGRESS', 'REVIEW', 'DEPLOYING', 'COMPLETED', 'FAILED']).optional(),
      },
      async ({ query, status }) => {
        const db = drizzle(this.env.DB, { schema });
        
        let requests = await db.select().from(schema.requests)
          .where(like(schema.requests.prompt, `%${query}%`))
          .orderBy(desc(schema.requests.createdAt))
          .limit(10);
        
        if (status) {
          requests = requests.filter(r => r.status === status);
        }
        
        return {
          content: [{
            type: 'text',
            text: JSON.stringify(requests, null, 2),
          }],
        };
      }
    );

    // Tool: Fix worker build failure
    this.server.tool(
      'fix_build_failure',
      'Analyze and fix a worker build failure',
      {
        workerName: z.string().describe('Name of the failed worker'),
      },
      async ({ workerName }) => {
        // This triggers the QA agent to analyze build logs and create a fix
        const db = drizzle(this.env.DB, { schema });
        
        const worker = await db.query.workersRegistry.findFirst({
          where: eq(schema.workersRegistry.workerName, workerName),
        });
        
        if (!worker) {
          return {
            content: [{ type: 'text', text: 'Worker not found' }],
            isError: true,
          };
        }
        
        // Trigger QA agent to fix
        const qaId = this.env.QA.idFromName(worker.requestId!);
        const qa = this.env.QA.get(qaId);
        await qa.fetch(new Request('http://internal/fix-build', {
          method: 'POST',
          body: JSON.stringify({ workerName, buildLogs: worker.lastBuildLogs }),
        }));
        
        return {
          content: [{
            type: 'text',
            text: `Build fix initiated for ${workerName}. A PR will be created with the fix.`,
          }],
        };
      }
    );

    // Resource: Request details
    this.server.resource(
      'request',
      'cloudforge://request/{id}',
      async (uri) => {
        const id = uri.pathname.split('/').pop();
        const db = drizzle(this.env.DB, { schema });
        const request = await db.query.requests.findFirst({
          where: eq(schema.requests.id, id!),
        });
        return JSON.stringify(request);
      }
    );
  }
}

// Export MCP routes
export const mcpRoutes = CloudForgeMCPServer.mount('/mcp');
```

### 3.6 Orchestrator Agent

Create `apps/api/src/agents/orchestrator.ts`:

```typescript
import { Agent } from 'agents';
import { drizzle } from 'drizzle-orm/d1';
import * as schema from '@cloudforge/db/schema';
import { broadcastUpdate } from '../websocket/handler';

interface OrchestratorState {
  requestId: string;
  currentPhase: 'PLANNING' | 'BUILDING' | 'REVIEWING' | 'DEPLOYING';
  activeTasks: string[];
}

export class OrchestratorAgent extends Agent<Env, OrchestratorState> {
  private db: ReturnType<typeof drizzle>;
  
  async onStart() {
    this.db = drizzle(this.env.DB, { schema });
  }

  async onRequest(request: Request): Promise<Response> {
    const url = new URL(request.url);
    
    if (url.pathname === '/start') {
      const { requestId } = await request.json() as { requestId: string };
      await this.startBuildProcess(requestId);
      return new Response(JSON.stringify({ status: 'started' }));
    }
    
    if (url.pathname === '/modify') {
      const { requestId, iterationId, prompt } = await request.json();
      await this.startModificationProcess(requestId, iterationId, prompt);
      return new Response(JSON.stringify({ status: 'modification_started' }));
    }
    
    return new Response('Not found', { status: 404 });
  }

  private async startBuildProcess(requestId: string) {
    // Update state
    this.setState({ requestId, currentPhase: 'PLANNING', activeTasks: [] });
    
    // Update request status
    await this.db.update(schema.requests)
      .set({ status: 'PLANNING' })
      .where(eq(schema.requests.id, requestId));
    
    // Broadcast status update
    broadcastUpdate({
      type: 'request_update',
      requestId,
      data: { status: 'PLANNING' },
      timestamp: new Date().toISOString(),
    });
    
    // Get the request details
    const request = await this.db.query.requests.findFirst({
      where: eq(schema.requests.id, requestId),
    });
    
    if (!request) return;
    
    // Step 1: Generate documentation queries and load Cloudflare docs
    const docsQueries = await this.generateDocsQueries(request.prompt);
    
    // Step 2: Load documentation context
    const docsContext = await this.loadCloudflareDocsContext(docsQueries);
    
    // Step 3: Create iteration
    const [iteration] = await this.db.insert(schema.iterations).values({
      requestId,
      iterationNumber: 1,
      status: 'PLANNING',
    }).returning();
    
    // Step 4: Delegate to Planner Agent
    const plannerId = this.env.PLANNER.idFromName(requestId);
    const planner = this.env.PLANNER.get(plannerId);
    
    await planner.fetch(new Request('http://internal/create-plan', {
      method: 'POST',
      body: JSON.stringify({
        requestId,
        iterationId: iteration.id,
        prompt: request.prompt,
        githubRepoUrls: request.githubRepoUrls ? JSON.parse(request.githubRepoUrls) : [],
        docsContext,
        docsQueries,
      }),
    }));
    
    // Log activity
    await this.logActivity(requestId, 'ORCHESTRATOR', 'Started build process', {
      docsQueriesGenerated: docsQueries,
    });
  }

  private async generateDocsQueries(prompt: string): Promise<string[]> {
    // Use Workers AI to generate relevant documentation search queries
    const response = await this.env.AI.run('@cf/meta/llama-3.1-70b-instruct', {
      messages: [
        {
          role: 'system',
          content: `You are a Cloudflare documentation expert. Given a user's request to build a Cloudflare Worker, generate 3-5 specific documentation search queries that would help understand the relevant APIs, bindings, and features needed.

Return ONLY a JSON array of search queries, nothing else. Example:
["Workers AI text generation binding", "D1 database drizzle ORM integration", "Hono framework Workers REST API"]`,
        },
        {
          role: 'user',
          content: prompt,
        },
      ],
      max_tokens: 500,
    }) as { response: string };
    
    try {
      return JSON.parse(response.response);
    } catch {
      // Fallback queries
      return [
        'Workers getting started tutorial',
        'Workers bindings configuration',
        'Workers deployment',
      ];
    }
  }

  private async loadCloudflareDocsContext(queries: string[]): Promise<Record<string, string>> {
    const context: Record<string, string> = {};
    
    // Connect to Cloudflare Docs MCP server
    await this.addMcpServer(
      'cloudflare-docs',
      'https://developers.cloudflare.com/mcp',
      undefined,
      undefined,
      { skipAuth: true }
    );
    
    const servers = this.getMcpServers();
    const docsServer = servers['cloudflare-docs'];
    
    if (docsServer?.tools) {
      for (const query of queries) {
        try {
          // Use the search tool from Cloudflare docs MCP
          const result = await this.callMcpTool('cloudflare-docs', 'search_cloudflare_documentation', {
            query,
          });
          context[query] = result;
        } catch (error) {
          console.error(`Failed to fetch docs for query: ${query}`, error);
        }
      }
    }
    
    return context;
  }

  private async logActivity(
    requestId: string,
    agent: string,
    action: string,
    data: any
  ) {
    await this.db.insert(schema.agentActivityLog).values({
      requestId,
      agentName: agent,
      action,
      output: JSON.stringify(data),
      status: 'SUCCESS',
    });
    
    broadcastUpdate({
      type: 'agent_activity',
      requestId,
      data: { agent, action, ...data },
      timestamp: new Date().toISOString(),
    });
  }

  // Called when a task is completed
  async onTaskCompleted(taskId: string, requestId: string) {
    const tasks = await this.db.select()
      .from(schema.tasks)
      .innerJoin(schema.plans, eq(schema.tasks.planId, schema.plans.id))
      .where(eq(schema.tasks.id, taskId));
    
    // Check if all tasks in current phase are complete
    const pendingTasks = await this.db.select()
      .from(schema.tasks)
      .where(and(
        eq(schema.tasks.planId, tasks[0].plans.id),
        notInArray(schema.tasks.status, ['COMPLETED', 'FAILED'])
      ));
    
    if (pendingTasks.length === 0) {
      // Move to next phase
      await this.progressToNextPhase(requestId);
    }
  }

  private async progressToNextPhase(requestId: string) {
    const currentPhase = this.state.currentPhase;
    
    const phaseOrder = ['PLANNING', 'BUILDING', 'REVIEWING', 'DEPLOYING'];
    const currentIndex = phaseOrder.indexOf(currentPhase);
    
    if (currentIndex < phaseOrder.length - 1) {
      const nextPhase = phaseOrder[currentIndex + 1] as OrchestratorState['currentPhase'];
      this.setState({ ...this.state, currentPhase: nextPhase });
      
      // Update request status
      const statusMap = {
        'BUILDING': 'IN_PROGRESS',
        'REVIEWING': 'REVIEW',
        'DEPLOYING': 'DEPLOYING',
      };
      
      await this.db.update(schema.requests)
        .set({ status: statusMap[nextPhase] || 'IN_PROGRESS' })
        .where(eq(schema.requests.id, requestId));
      
      broadcastUpdate({
        type: 'request_update',
        requestId,
        data: { status: statusMap[nextPhase], phase: nextPhase },
        timestamp: new Date().toISOString(),
      });
    } else {
      // All phases complete
      await this.db.update(schema.requests)
        .set({ status: 'COMPLETED' })
        .where(eq(schema.requests.id, requestId));
      
      broadcastUpdate({
        type: 'request_update',
        requestId,
        data: { status: 'COMPLETED' },
        timestamp: new Date().toISOString(),
      });
    }
  }
}
```

### 3.7 Planner Agent

Create `apps/api/src/agents/planner.ts`:

```typescript
import { Agent } from 'agents';
import { drizzle } from 'drizzle-orm/d1';
import * as schema from '@cloudforge/db/schema';
import { broadcastUpdate } from '../websocket/handler';

interface PlannerState {
  requestId: string;
  iterationId: string;
  planId: string;
}

export class PlannerAgent extends Agent<Env, PlannerState> {
  private db: ReturnType<typeof drizzle>;
  
  async onStart() {
    this.db = drizzle(this.env.DB, { schema });
  }

  async onRequest(request: Request): Promise<Response> {
    const url = new URL(request.url);
    
    if (url.pathname === '/create-plan') {
      const body = await request.json();
      await this.createPlan(body);
      return new Response(JSON.stringify({ status: 'plan_created' }));
    }
    
    return new Response('Not found', { status: 404 });
  }

  private async createPlan(params: {
    requestId: string;
    iterationId: string;
    prompt: string;
    githubRepoUrls: string[];
    docsContext: Record<string, string>;
    docsQueries: string[];
  }) {
    const { requestId, iterationId, prompt, githubRepoUrls, docsContext, docsQueries } = params;
    
    // Get agent configuration
    const config = await this.db.query.agentConfigurations.findFirst({
      where: eq(schema.agentConfigurations.agentName, 'PLANNER'),
    });
    
    const systemPrompt = config?.systemPrompt || this.getDefaultSystemPrompt();
    
    // Build context for AI
    const contextStr = Object.entries(docsContext)
      .map(([query, content]) => `### ${query}\n${content}`)
      .join('\n\n');
    
    // Generate plan using Workers AI
    const response = await this.env.AI.run(
      config?.modelId || '@cf/meta/llama-3.1-70b-instruct',
      {
        messages: [
          { role: 'system', content: systemPrompt },
          {
            role: 'user',
            content: `
## User Request
${prompt}

## Reference GitHub Repositories
${githubRepoUrls.length > 0 ? githubRepoUrls.join('\n') : 'None provided'}

## Cloudflare Documentation Context
${contextStr}

Generate a detailed plan to build this worker. Return a JSON object with:
{
  "summary": "Brief summary of what will be built",
  "architecture": {
    "components": ["list of components"],
    "bindings": ["D1", "R2", "KV", "AI", etc.],
    "frameworks": ["Hono", "Drizzle", etc.]
  },
  "tasks": [
    {
      "title": "Task title",
      "description": "Detailed description",
      "assignedAgent": "BACKEND|UX|DATA_ENGINEER|API|DOCUMENTATION|QA",
      "priority": 1-10,
      "estimatedComplexity": "LOW|MEDIUM|HIGH",
      "dependencies": [] // IDs of tasks this depends on
    }
  ]
}`,
          },
        ],
        max_tokens: 4000,
      }
    ) as { response: string };
    
    // Parse the plan
    let plan;
    try {
      // Extract JSON from response (handle markdown code blocks)
      const jsonMatch = response.response.match(/```json\n?([\s\S]*?)\n?```/) || 
                        response.response.match(/\{[\s\S]*\}/);
      plan = JSON.parse(jsonMatch ? jsonMatch[1] || jsonMatch[0] : response.response);
    } catch (error) {
      console.error('Failed to parse plan:', error);
      throw new Error('Failed to generate valid plan');
    }
    
    // Save plan to database
    const [savedPlan] = await this.db.insert(schema.plans).values({
      iterationId,
      planJson: JSON.stringify(plan),
      docsQueriesGenerated: JSON.stringify(docsQueries),
      docsContextLoaded: JSON.stringify(docsContext),
    }).returning();
    
    // Create tasks from plan
    const taskIdMap = new Map<number, string>();
    
    for (let i = 0; i < plan.tasks.length; i++) {
      const task = plan.tasks[i];
      const [savedTask] = await this.db.insert(schema.tasks).values({
        planId: savedPlan.id,
        title: task.title,
        description: task.description,
        assignedAgent: task.assignedAgent,
        priority: task.priority || i,
        estimatedComplexity: task.estimatedComplexity || 'MEDIUM',
        dependencies: task.dependencies ? JSON.stringify(task.dependencies) : null,
        status: 'TODO',
      }).returning();
      
      taskIdMap.set(i, savedTask.id);
    }
    
    // Update state
    this.setState({ requestId, iterationId, planId: savedPlan.id });
    
    // Broadcast plan creation
    broadcastUpdate({
      type: 'plan_created',
      requestId,
      data: {
        planId: savedPlan.id,
        summary: plan.summary,
        taskCount: plan.tasks.length,
      },
      timestamp: new Date().toISOString(),
    });
    
    // Update iteration status
    await this.db.update(schema.iterations)
      .set({ status: 'EXECUTING' })
      .where(eq(schema.iterations.id, iterationId));
    
    // Dispatch tasks to appropriate agents
    await this.dispatchTasks(requestId, savedPlan.id, plan.tasks, taskIdMap);
    
    return savedPlan;
  }

  private async dispatchTasks(
    requestId: string,
    planId: string,
    tasks: any[],
    taskIdMap: Map<number, string>
  ) {
    // Group tasks by agent
    const tasksByAgent = new Map<string, any[]>();
    
    for (const task of tasks) {
      const agent = task.assignedAgent;
      if (!tasksByAgent.has(agent)) {
        tasksByAgent.set(agent, []);
      }
      tasksByAgent.get(agent)!.push({
        ...task,
        id: taskIdMap.get(tasks.indexOf(task)),
      });
    }
    
    // Dispatch to each agent
    const agentBindings: Record<string, DurableObjectNamespace> = {
      'BACKEND': this.env.BACKEND,
      'UX': this.env.UX,
      'DATA_ENGINEER': this.env.DATA_ENGINEER,
      'API': this.env.API,
      'DOCUMENTATION': this.env.DOCUMENTATION,
      'QA': this.env.QA,
    };
    
    for (const [agentName, agentTasks] of tasksByAgent) {
      const namespace = agentBindings[agentName];
      if (namespace) {
        const agentId = namespace.idFromName(requestId);
        const agent = namespace.get(agentId);
        
        await agent.fetch(new Request('http://internal/assign-tasks', {
          method: 'POST',
          body: JSON.stringify({
            requestId,
            planId,
            tasks: agentTasks,
          }),
        }));
      }
    }
  }

  private getDefaultSystemPrompt(): string {
    return `You are the Planning Agent for CloudForge, an AI-powered Cloudflare Worker builder.

Your role is to:
1. Analyze user requests and break them into actionable tasks
2. Identify required Cloudflare bindings (D1, R2, KV, AI, Vectorize, etc.)
3. Determine the best frameworks and patterns (Hono, Drizzle, React, etc.)
4. Create a comprehensive task list for the development team

Task Assignment Guidelines:
- BACKEND: Server-side logic, API implementation, Worker code
- UX: Frontend components, React/shadcn UI, user experience
- DATA_ENGINEER: Database schema, migrations, Drizzle ORM, data modeling
- API: REST/WebSocket API design, OpenAPI specs, request/response handling
- DOCUMENTATION: README, API docs, inline comments, usage examples
- QA: Testing, validation, error handling, build verification

Always:
- Use Drizzle ORM for all D1 database interactions
- Use Hono for REST APIs with Zod validation
- Include OpenAPI 3.1.0 specifications
- Plan for WebSocket support where realtime updates are needed
- Consider MCP server exposure for AI integration`;
  }
}
```

### 3.8 Backend Agent (with Sandbox SDK)

Create `apps/api/src/agents/backend.ts`:

```typescript
import { Agent } from 'agents';
import { getSandbox } from '@cloudflare/sandbox';
import { drizzle } from 'drizzle-orm/d1';
import * as schema from '@cloudforge/db/schema';
import { broadcastUpdate } from '../websocket/handler';

interface BackendState {
  requestId: string;
  currentTaskId: string | null;
  sandboxSessionId: string | null;
}

export class BackendAgent extends Agent<Env, BackendState> {
  private db: ReturnType<typeof drizzle>;
  
  async onStart() {
    this.db = drizzle(this.env.DB, { schema });
  }

  async onRequest(request: Request): Promise<Response> {
    const url = new URL(request.url);
    
    if (url.pathname === '/assign-tasks') {
      const { requestId, planId, tasks } = await request.json();
      await this.processTasks(requestId, planId, tasks);
      return new Response(JSON.stringify({ status: 'tasks_assigned' }));
    }
    
    return new Response('Not found', { status: 404 });
  }

  private async processTasks(requestId: string, planId: string, tasks: any[]) {
    // Sort tasks by priority and dependencies
    const sortedTasks = this.topologicalSort(tasks);
    
    // Get the request and plan context
    const request = await this.db.query.requests.findFirst({
      where: eq(schema.requests.id, requestId),
    });
    
    const plan = await this.db.query.plans.findFirst({
      where: eq(schema.plans.id, planId),
    });
    
    // Initialize sandbox
    const sandbox = getSandbox(this.env.Sandbox, `backend-${requestId}`);
    
    // Clone the starter kit or reference repos
    if (request?.githubRepoUrls) {
      const repoUrls = JSON.parse(request.githubRepoUrls);
      for (const repoUrl of repoUrls) {
        await sandbox.gitCheckout(repoUrl, { depth: 1 });
      }
    }
    
    // Fork the core-react-starter-kit for the new worker
    const workerName = request?.workerName || `worker-${requestId}`;
    await this.createNewWorkerRepo(sandbox, workerName, requestId);
    
    // Process each task
    for (const task of sortedTasks) {
      await this.executeTask(sandbox, task, requestId, request!, plan!);
    }
  }

  private async createNewWorkerRepo(sandbox: any, workerName: string, requestId: string) {
    // Use Python script in sandbox to fork and create new repo
    const createRepoScript = `
import os
from github import Github
import subprocess

# GitHub setup
g = Github(os.environ.get('GITHUB_TOKEN'))
org = g.get_organization(os.environ.get('GITHUB_ORG', 'your-org'))

# Fork the starter kit
source_repo = g.get_repo('jmbish04/core-react-starter-kit')
new_repo = org.create_repo(
    name='${workerName}',
    description='CloudForge generated worker: ${workerName}',
    private=True,
    auto_init=False
)

# Clone and push to new repo
subprocess.run(['git', 'clone', '--depth=1', source_repo.clone_url, '/workspace/${workerName}'])
os.chdir('/workspace/${workerName}')
subprocess.run(['git', 'remote', 'set-url', 'origin', new_repo.clone_url])
subprocess.run(['git', 'push', '-u', 'origin', 'main'])

print(f"REPO_URL:{new_repo.html_url}")
print(f"CLONE_URL:{new_repo.clone_url}")
`;
    
    await sandbox.writeFile('/workspace/create_repo.py', createRepoScript);
    const result = await sandbox.exec('python /workspace/create_repo.py');
    
    // Parse output for repo URL
    const repoUrlMatch = result.stdout.match(/REPO_URL:(.+)/);
    if (repoUrlMatch) {
      await this.db.update(schema.requests)
        .set({ githubRepoCreated: repoUrlMatch[1] })
        .where(eq(schema.requests.id, requestId));
      
      // Register worker
      await this.db.insert(schema.workersRegistry).values({
        requestId,
        workerName,
        githubRepoUrl: repoUrlMatch[1],
      });
    }
  }

  private async executeTask(
    sandbox: any,
    task: any,
    requestId: string,
    request: typeof schema.requests.$inferSelect,
    plan: typeof schema.plans.$inferSelect
  ) {
    // Update task status
    await this.db.update(schema.tasks)
      .set({ status: 'IN_PROGRESS', startedAt: new Date() })
      .where(eq(schema.tasks.id, task.id));
    
    broadcastUpdate({
      type: 'task_update',
      requestId,
      data: { taskId: task.id, status: 'IN_PROGRESS' },
      timestamp: new Date().toISOString(),
    });
    
    try {
      // Get agent configuration for code generation
      const config = await this.db.query.agentConfigurations.findFirst({
        where: eq(schema.agentConfigurations.agentName, 'BACKEND'),
      });
      
      // Load relevant docs context
      const planData = JSON.parse(plan.planJson);
      const docsContext = plan.docsContextLoaded ? JSON.parse(plan.docsContextLoaded) : {};
      
      // Generate code using Workers AI
      const codeGenResponse = await this.env.AI.run(
        config?.modelId || '@cf/meta/llama-3.1-70b-instruct',
        {
          messages: [
            {
              role: 'system',
              content: config?.systemPrompt || this.getDefaultSystemPrompt(),
            },
            {
              role: 'user',
              content: `
## Task
${task.title}

## Description
${task.description}

## Project Context
Worker Name: ${request.workerName}
Original Request: ${request.prompt}
Architecture: ${JSON.stringify(planData.architecture, null, 2)}

## Cloudflare Documentation Reference
${Object.entries(docsContext).map(([q, c]) => `### ${q}\n${c}`).join('\n\n')}

Generate the code to complete this task. Return a JSON object with:
{
  "files": [
    {
      "path": "relative/path/to/file.ts",
      "content": "file content here",
      "action": "create" | "update" | "delete"
    }
  ],
  "commands": ["npm install package-name", "other commands to run"],
  "notes": "Any implementation notes"
}`,
            },
          ],
          max_tokens: 8000,
        }
      ) as { response: string };
      
      // Parse and execute code changes
      const codeChanges = JSON.parse(
        codeGenResponse.response.match(/```json\n?([\s\S]*?)\n?```/)?.[1] || 
        codeGenResponse.response
      );
      
      // Apply file changes in sandbox
      for (const file of codeChanges.files) {
        const fullPath = `/workspace/${request.workerName}/${file.path}`;
        
        if (file.action === 'delete') {
          await sandbox.deleteFile(fullPath);
        } else {
          // Ensure directory exists
          const dir = fullPath.substring(0, fullPath.lastIndexOf('/'));
          await sandbox.exec(`mkdir -p ${dir}`);
          await sandbox.writeFile(fullPath, file.content);
        }
      }
      
      // Run any commands
      for (const command of codeChanges.commands || []) {
        await sandbox.exec(`cd /workspace/${request.workerName} && ${command}`);
      }
      
      // Commit changes
      await sandbox.exec(`
        cd /workspace/${request.workerName} && 
        git add -A && 
        git commit -m "Task: ${task.title}" && 
        git push
      `);
      
      // Update task status
      await this.db.update(schema.tasks)
        .set({
          status: 'PENDING_PEER_REVIEW',
          completedAt: new Date(),
          agentNotes: codeChanges.notes,
          outputArtifacts: JSON.stringify(codeChanges.files.map((f: any) => f.path)),
        })
        .where(eq(schema.tasks.id, task.id));
      
      broadcastUpdate({
        type: 'task_update',
        requestId,
        data: { taskId: task.id, status: 'PENDING_PEER_REVIEW' },
        timestamp: new Date().toISOString(),
      });
      
    } catch (error) {
      await this.db.update(schema.tasks)
        .set({
          status: 'FAILED',
          agentNotes: `Error: ${error instanceof Error ? error.message : String(error)}`,
        })
        .where(eq(schema.tasks.id, task.id));
      
      broadcastUpdate({
        type: 'task_update',
        requestId,
        data: { taskId: task.id, status: 'FAILED', error: String(error) },
        timestamp: new Date().toISOString(),
      });
    }
  }

  private topologicalSort(tasks: any[]): any[] {
    // Simple topological sort based on dependencies
    const sorted: any[] = [];
    const visited = new Set<string>();
    
    const visit = (task: any) => {
      if (visited.has(task.id)) return;
      visited.add(task.id);
      
      const deps = task.dependencies ? JSON.parse(task.dependencies) : [];
      for (const depId of deps) {
        const depTask = tasks.find(t => t.id === depId);
        if (depTask) visit(depTask);
      }
      
      sorted.push(task);
    };
    
    for (const task of tasks) {
      visit(task);
    }
    
    return sorted;
  }

  private getDefaultSystemPrompt(): string {
    return `You are the Backend Development Agent for CloudForge.

Your responsibilities:
- Write clean, production-ready TypeScript code
- Implement Cloudflare Worker logic and handlers
- Use Hono for REST APIs with proper middleware
- Implement WebSocket handlers when needed
- Follow Cloudflare Workers best practices

Technical Requirements:
- Always use TypeScript with strict typing
- Use Hono framework for HTTP handling
- Use Drizzle ORM for database operations (never raw SQL in workers)
- Implement proper error handling and logging
- Follow the monorepo structure (apps/api for backend)
- Export all necessary Durable Object classes
- Use environment bindings correctly (env.DB, env.AI, etc.)

Code Style:
- Use async/await consistently
- Add JSDoc comments for public functions
- Use meaningful variable names
- Keep functions focused and small`;
  }
}
```

### 3.9 Data Engineer Agent

Create `apps/api/src/agents/data-engineer.ts`:

```typescript
import { Agent } from 'agents';
import { getSandbox } from '@cloudflare/sandbox';
import { drizzle } from 'drizzle-orm/d1';
import * as schema from '@cloudforge/db/schema';
import { broadcastUpdate } from '../websocket/handler';

export class DataEngineerAgent extends Agent<Env, { requestId: string }> {
  private db: ReturnType<typeof drizzle>;
  
  async onStart() {
    this.db = drizzle(this.env.DB, { schema });
  }

  async onRequest(request: Request): Promise<Response> {
    const url = new URL(request.url);
    
    if (url.pathname === '/assign-tasks') {
      const { requestId, planId, tasks } = await request.json();
      await this.processTasks(requestId, planId, tasks);
      return new Response(JSON.stringify({ status: 'tasks_assigned' }));
    }
    
    return new Response('Not found', { status: 404 });
  }

  private async processTasks(requestId: string, planId: string, tasks: any[]) {
    const sandbox = getSandbox(this.env.Sandbox, `data-eng-${requestId}`);
    
    const request = await this.db.query.requests.findFirst({
      where: eq(schema.requests.id, requestId),
    });
    
    const plan = await this.db.query.plans.findFirst({
      where: eq(schema.plans.id, planId),
    });
    
    for (const task of tasks) {
      await this.executeDataTask(sandbox, task, requestId, request!, plan!);
    }
  }

  private async executeDataTask(
    sandbox: any,
    task: any,
    requestId: string,
    request: typeof schema.requests.$inferSelect,
    plan: typeof schema.plans.$inferSelect
  ) {
    await this.db.update(schema.tasks)
      .set({ status: 'IN_PROGRESS', startedAt: new Date() })
      .where(eq(schema.tasks.id, task.id));
    
    broadcastUpdate({
      type: 'task_update',
      requestId,
      data: { taskId: task.id, status: 'IN_PROGRESS' },
      timestamp: new Date().toISOString(),
    });

    try {
      const config = await this.db.query.agentConfigurations.findFirst({
        where: eq(schema.agentConfigurations.agentName, 'DATA_ENGINEER'),
      });
      
      const planData = JSON.parse(plan.planJson);
      
      // Generate Drizzle schema and migrations
      const schemaGenResponse = await this.env.AI.run(
        config?.modelId || '@cf/meta/llama-3.1-70b-instruct',
        {
          messages: [
            {
              role: 'system',
              content: config?.systemPrompt || this.getDefaultSystemPrompt(),
            },
            {
              role: 'user',
              content: `
## Task
${task.title}

## Description
${task.description}

## Project Context
Worker Name: ${request.workerName}
Original Request: ${request.prompt}
Architecture: ${JSON.stringify(planData.architecture, null, 2)}

Generate the Drizzle ORM schema and configuration. Return a JSON object with:
{
  "files": [
    {
      "path": "packages/db/src/schema.ts",
      "content": "// Drizzle schema content",
      "action": "create"
    },
    {
      "path": "packages/db/drizzle.config.ts",
      "content": "// Drizzle config",
      "action": "create"
    }
  ],
  "bindings": [
    {
      "type": "d1_databases",
      "name": "${request.workerName}-db",
      "binding": "DB"
    }
  ],
  "migrations": ["migration SQL statements if needed"],
  "notes": "Schema design notes"
}`,
            },
          ],
          max_tokens: 6000,
        }
      ) as { response: string };
      
      const schemaChanges = JSON.parse(
        schemaGenResponse.response.match(/```json\n?([\s\S]*?)\n?```/)?.[1] || 
        schemaGenResponse.response
      );
      
      // Apply schema files
      for (const file of schemaChanges.files) {
        const fullPath = `/workspace/${request.workerName}/${file.path}`;
        const dir = fullPath.substring(0, fullPath.lastIndexOf('/'));
        await sandbox.exec(`mkdir -p ${dir}`);
        await sandbox.writeFile(fullPath, file.content);
      }
      
      // Create D1 database and bindings using Cloudflare API
      await this.createBindings(request.workerName!, schemaChanges.bindings);
      
      // Run Drizzle migrations
      await sandbox.exec(`
        cd /workspace/${request.workerName} && 
        npm install drizzle-orm drizzle-kit &&
        npx drizzle-kit generate
      `);
      
      // Commit changes
      await sandbox.exec(`
        cd /workspace/${request.workerName} && 
        git add -A && 
        git commit -m "feat: Add database schema - ${task.title}" && 
        git push
      `);
      
      await this.db.update(schema.tasks)
        .set({
          status: 'PENDING_PEER_REVIEW',
          completedAt: new Date(),
          agentNotes: schemaChanges.notes,
          outputArtifacts: JSON.stringify(schemaChanges.files.map((f: any) => f.path)),
        })
        .where(eq(schema.tasks.id, task.id));
      
      broadcastUpdate({
        type: 'task_update',
        requestId,
        data: { taskId: task.id, status: 'PENDING_PEER_REVIEW' },
        timestamp: new Date().toISOString(),
      });
      
    } catch (error) {
      await this.db.update(schema.tasks)
        .set({
          status: 'FAILED',
          agentNotes: `Error: ${error instanceof Error ? error.message : String(error)}`,
        })
        .where(eq(schema.tasks.id, task.id));
      
      broadcastUpdate({
        type: 'task_update',
        requestId,
        data: { taskId: task.id, status: 'FAILED', error: String(error) },
        timestamp: new Date().toISOString(),
      });
    }
  }

  private async createBindings(workerName: string, bindings: any[]) {
    // Use Cloudflare API to create D1 databases, KV namespaces, R2 buckets, etc.
    const cloudflare = new (await import('cloudflare')).default({
      apiToken: this.env.CLOUDFLARE_API_TOKEN,
    });
    
    for (const binding of bindings) {
      if (binding.type === 'd1_databases') {
        // Create D1 database
        const database = await cloudflare.d1.database.create({
          account_id: this.env.CLOUDFLARE_ACCOUNT_ID,
          name: binding.name,
        });
        
        // Update worker registry with binding info
        await this.db.update(schema.workersRegistry)
          .set({
            bindingsCreated: sql`json_set(COALESCE(bindings_created, '[]'), '$[#]', ${JSON.stringify({
              type: 'd1',
              name: binding.name,
              id: database.result?.uuid,
            })})`,
          })
          .where(eq(schema.workersRegistry.workerName, workerName));
      }
      
      // Add handlers for KV, R2, Vectorize, etc.
    }
  }

  private getDefaultSystemPrompt(): string {
    return `You are the Data Engineering Agent for CloudForge.

Your responsibilities:
- Design database schemas using Drizzle ORM for D1
- Create proper migrations and indexes
- Define relationships between tables
- Configure Drizzle for Cloudflare D1

Technical Requirements:
- ALWAYS use Drizzle ORM - never raw SQL in application code
- Use drizzle-orm/sqlite-core for D1 databases
- Define proper types and relations
- Include indexes for frequently queried columns
- Use cuid2 or nanoid for primary keys
- Add created_at/updated_at timestamps to all tables

Schema Best Practices:
- Use snake_case for column names
- Define foreign key relationships explicitly
- Add proper NOT NULL constraints
- Use enums for status fields
- Include JSON columns for flexible metadata
- Design for the monorepo structure (packages/db)`;
  }
}
```

## PHASE 4: FRONTEND WORKER (apps/app)

### 4.1 Frontend Wrangler Configuration

Create `apps/app/wrangler.jsonc`:

```jsonc
{
  "$schema": "./node_modules/wrangler/config-schema.json",
  "name": "cloudforge-app",
  "compatibility_date": "2025-10-13",
  "assets": {
    "directory": "./dist"
  },
  "vars": {
    "API_URL": "https://cloudforge-api.workers.dev"
  }
}
```

### 4.2 Main App Component

Create `apps/app/src/App.tsx`:

```tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from '@/components/theme-provider';
import { Toaster } from '@/components/ui/toaster';
import { WebSocketProvider } from '@/contexts/websocket';

// Pages
import { Dashboard } from '@/pages/Dashboard';
import { RequestDetails } from '@/pages/RequestDetails';
import { NewRequest } from '@/pages/NewRequest';
import { WorkersList } from '@/pages/WorkersList';
import { WorkerDetails } from '@/pages/WorkerDetails';
import { AgentConfig } from '@/pages/AgentConfig';
import { FutureFeatures } from '@/pages/FutureFeatures';

const queryClient = new QueryClient();

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider defaultTheme="dark" storageKey="cloudforge-theme">
        <WebSocketProvider url={`${import.meta.env.VITE_API_URL}/ws`}>
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/requests/new" element={<NewRequest />} />
              <Route path="/requests/:id" element={<RequestDetails />} />
              <Route path="/workers" element={<WorkersList />} />
              <Route path="/workers/:name" element={<WorkerDetails />} />
              <Route path="/agents/config" element={<AgentConfig />} />
              <Route path="/roadmap" element={<FutureFeatures />} />
            </Routes>
          </BrowserRouter>
          <Toaster />
        </WebSocketProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
```

### 4.3 WebSocket Context for Realtime Updates

Create `apps/app/src/contexts/websocket.tsx`:

```tsx
import { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react';

interface WebSocketMessage {
  type: 'task_update' | 'request_update' | 'agent_activity' | 'plan_created';
  requestId: string;
  data: any;
  timestamp: string;
}

interface WebSocketContextValue {
  isConnected: boolean;
  subscribe: (requestId: string) => void;
  unsubscribe: (requestId: string) => void;
  lastMessage: WebSocketMessage | null;
  messages: WebSocketMessage[];
}

const WebSocketContext = createContext<WebSocketContextValue | null>(null);

export function WebSocketProvider({ 
  url, 
  children 
}: { 
  url: string; 
  children: ReactNode;
}) {
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [messages, setMessages] = useState<WebSocketMessage[]>([]);

  useEffect(() => {
    const ws = new WebSocket(url);
    
    ws.onopen = () => {
      setIsConnected(true);
      setSocket(ws);
    };
    
    ws.onmessage = (event) => {
      const message: WebSocketMessage = JSON.parse(event.data);
      setLastMessage(message);
      setMessages((prev) => [...prev.slice(-100), message]); // Keep last 100
    };
    
    ws.onclose = () => {
      setIsConnected(false);
      // Reconnect after 3 seconds
      setTimeout(() => {
        setSocket(null);
      }, 3000);
    };
    
    return () => {
      ws.close();
    };
  }, [url]);

  const subscribe = useCallback((requestId: string) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: 'subscribe', requestId }));
    }
  }, [socket]);

  const unsubscribe = useCallback((requestId: string) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: 'unsubscribe', requestId }));
    }
  }, [socket]);

  return (
    <WebSocketContext.Provider value={{
      isConnected,
      subscribe,
      unsubscribe,
      lastMessage,
      messages,
    }}>
      {children}
    </WebSocketContext.Provider>
  );
}

export function useWebSocket() {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within WebSocketProvider');
  }
  return context;
}

// Hook for subscribing to a specific request
export function useRequestUpdates(requestId: string) {
  const { subscribe, unsubscribe, messages } = useWebSocket();
  
  useEffect(() => {
    if (requestId) {
      subscribe(requestId);
      return () => unsubscribe(requestId);
    }
  }, [requestId, subscribe, unsubscribe]);
  
  return messages.filter((m) => m.requestId === requestId);
}
```

### 4.4 Request Details Page with Backlog View

Create `apps/app/src/pages/RequestDetails.tsx`:

```tsx
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useRequestUpdates } from '@/contexts/websocket';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  CheckCircle, 
  Clock, 
  AlertCircle, 
  Loader2, 
  GitBranch,
  ExternalLink 
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

const statusColors = {
  TODO: 'bg-gray-500',
  IN_PROGRESS: 'bg-blue-500 animate-pulse',
  PENDING_PEER_REVIEW: 'bg-yellow-500',
  IN_REVIEW: 'bg-purple-500',
  BLOCKED: 'bg-red-500',
  COMPLETED: 'bg-green-500',
  FAILED: 'bg-red-600',
};

const StatusIcon = ({ status }: { status: string }) => {
  switch (status) {
    case 'COMPLETED':
      return <CheckCircle className="h-4 w-4 text-green-500" />;
    case 'IN_PROGRESS':
      return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />;
    case 'FAILED':
      return <AlertCircle className="h-4 w-4 text-red-500" />;
    default:
      return <Clock className="h-4 w-4 text-gray-400" />;
  }
};

export function RequestDetails() {
  const { id } = useParams<{ id: string }>();
  const updates = useRequestUpdates(id!);
  
  const { data: request, isLoading } = useQuery({
    queryKey: ['request', id],
    queryFn: async () => {
      const res = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/requests/${id}`);
      return res.json();
    },
    refetchInterval: 5000, // Fallback polling
  });

  // Merge realtime updates with fetched data
  const latestTasks = request?.iterations?.[0]?.plans?.[0]?.tasks?.map((task: any) => {
    const update = updates.find(
      (u) => u.type === 'task_update' && u.data.taskId === task.id
    );
    return update ? { ...task, status: update.data.status } : task;
  }) || [];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  const completedTasks = latestTasks.filter((t: any) => t.status === 'COMPLETED').length;
  const totalTasks = latestTasks.length;
  const progress = totalTasks > 0 ? (completedTasks / totalTasks) * 100 : 0;

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">{request?.workerName || 'Building Worker...'}</h1>
          <p className="text-muted-foreground mt-1">{request?.prompt}</p>
        </div>
        <div className="flex items-center gap-4">
          <Badge variant={request?.status === 'COMPLETED' ? 'success' : 'default'}>
            {request?.status}
          </Badge>
          {request?.githubRepoCreated && (
            <a 
              href={request.githubRepoCreated} 
              target="_blank" 
              rel="noopener noreferrer"
              className="flex items-center gap-2 text-sm text-blue-500 hover:underline"
            >
              <GitBranch className="h-4 w-4" />
              View Repository
              <ExternalLink className="h-3 w-3" />
            </a>
          )}
        </div>
      </div>

      {/* Progress Overview */}
      <Card>
        <CardHeader>
          <CardTitle>Build Progress</CardTitle>
</CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>{completedTasks} of {totalTasks} tasks completed</span>
              <span>{Math.round(progress)}%</span>
            </div>
            <Progress value={progress} />
          </div>
        </CardContent>
      </Card>

      {/* Iterations and Tasks */}
      <Tabs defaultValue="backlog">
        <TabsList>
          <TabsTrigger value="backlog">Backlog</TabsTrigger>
          <TabsTrigger value="activity">Activity Log</TabsTrigger>
          <TabsTrigger value="artifacts">Artifacts</TabsTrigger>
        </TabsList>

        <TabsContent value="backlog" className="space-y-4">
          {request?.iterations?.map((iteration: any, idx: number) => (
            <Card key={iteration.id}>
              <CardHeader>
                <CardTitle className="text-lg">
                  Iteration {iteration.iterationNumber}
                  <Badge className="ml-2" variant="outline">
                    {iteration.status}
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[400px]">
                  <div className="space-y-2">
                    {iteration.plans?.[0]?.tasks?.map((task: any) => {
                      const liveTask = latestTasks.find((t: any) => t.id === task.id) || task;
                      return (
                        <div
                          key={task.id}
                          className="flex items-center justify-between p-3 rounded-lg border bg-card hover:bg-accent/50 transition-colors"
                        >
                          <div className="flex items-center gap-3">
                            <StatusIcon status={liveTask.status} />
                            <div>
                              <p className="font-medium">{task.title}</p>
                              <p className="text-sm text-muted-foreground">
                                Assigned to: {task.assignedAgent}
                              </p>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <Badge 
                              className={statusColors[liveTask.status as keyof typeof statusColors]}
                            >
                              {liveTask.status.replace(/_/g, ' ')}
                            </Badge>
                            {task.completedAt && (
                              <span className="text-xs text-muted-foreground">
                                {formatDistanceToNow(new Date(task.completedAt), { addSuffix: true })}
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          ))}
        </TabsContent>

        <TabsContent value="activity">
          <Card>
            <CardContent className="pt-6">
              <ScrollArea className="h-[500px]">
                <div className="space-y-4">
                  {updates.map((update, idx) => (
                    <div key={idx} className="flex items-start gap-3 p-3 rounded border">
                      <div className="flex-1">
                        <p className="font-medium">{update.type}</p>
                        <pre className="text-xs bg-muted p-2 rounded mt-2 overflow-x-auto">
                          {JSON.stringify(update.data, null, 2)}
                        </pre>
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {formatDistanceToNow(new Date(update.timestamp), { addSuffix: true })}
                      </span>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="artifacts">
          {/* Show generated files and artifacts */}
          <Card>
            <CardContent className="pt-6">
              <p className="text-muted-foreground">
                Artifacts will appear here as they are generated...
              </p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
```

### 4.5 Agent Configuration Page

Create `apps/app/src/pages/AgentConfig.tsx`:

```tsx
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Save, Plus, Trash2 } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

const AGENT_NAMES = [
  'ORCHESTRATOR',
  'PLANNER',
  'BACKEND',
  'UX',
  'DATA_ENGINEER',
  'API',
  'DOCUMENTATION',
  'QA',
] as const;

const AVAILABLE_MODELS = [
  '@cf/meta/llama-3.1-70b-instruct',
  '@cf/meta/llama-3.1-8b-instruct',
  '@cf/deepseek-ai/deepseek-r1-distill-qwen-32b',
  '@cf/mistral/mistral-7b-instruct-v0.1',
];

export function AgentConfig() {
  const [selectedAgent, setSelectedAgent] = useState<string>(AGENT_NAMES[0]);
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data: configs, isLoading } = useQuery({
    queryKey: ['agent-configs'],
    queryFn: async () => {
      const res = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/agents/config`);
      return res.json();
    },
  });

  const updateConfig = useMutation({
    mutationFn: async (config: any) => {
      const res = await fetch(
        `${import.meta.env.VITE_API_URL}/api/v1/agents/config/${config.agentName}`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(config),
        }
      );
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agent-configs'] });
      toast({
        title: 'Configuration saved',
        description: `${selectedAgent} agent configuration updated successfully.`,
      });
    },
  });

  const currentConfig = configs?.find((c: any) => c.agentName === selectedAgent) || {
    agentName: selectedAgent,
    systemPrompt: '',
    modelId: '@cf/meta/llama-3.1-70b-instruct',
    temperature: 0.7,
    maxTokens: 4096,
    mcpServersConfig: '[]',
    toolsEnabled: '[]',
    constraints: '{}',
  };

  const [formData, setFormData] = useState(currentConfig);

  const handleSave = () => {
    updateConfig.mutate(formData);
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Agent Configuration</h1>
        <p className="text-muted-foreground mt-1">
          Configure prompts, models, and tools for each agent in the build team
        </p>
      </div>

      <div className="grid grid-cols-12 gap-6">
        {/* Agent List */}
        <div className="col-span-3">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Agents</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {AGENT_NAMES.map((name) => (
                <button
                  key={name}
                  onClick={() => {
                    setSelectedAgent(name);
                    const config = configs?.find((c: any) => c.agentName === name);
                    if (config) setFormData(config);
                  }}
                  className={`w-full text-left px-3 py-2 rounded-lg transition-colors ${
                    selectedAgent === name
                      ? 'bg-primary text-primary-foreground'
                      : 'hover:bg-accent'
                  }`}
                >
                  {name.replace(/_/g, ' ')}
                </button>
              ))}
            </CardContent>
          </Card>
        </div>

        {/* Configuration Form */}
        <div className="col-span-9 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>{selectedAgent.replace(/_/g, ' ')} Configuration</CardTitle>
              <CardDescription>
                Customize how this agent behaves during the build process
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="prompt">
                <TabsList>
                  <TabsTrigger value="prompt">System Prompt</TabsTrigger>
                  <TabsTrigger value="model">Model Settings</TabsTrigger>
                  <TabsTrigger value="mcp">MCP Servers</TabsTrigger>
                  <TabsTrigger value="constraints">Constraints</TabsTrigger>
                </TabsList>

                <TabsContent value="prompt" className="space-y-4 pt-4">
                  <div className="space-y-2">
                    <Label htmlFor="systemPrompt">System Prompt</Label>
                    <Textarea
                      id="systemPrompt"
                      value={formData.systemPrompt}
                      onChange={(e) => setFormData({ ...formData, systemPrompt: e.target.value })}
                      rows={15}
                      className="font-mono text-sm"
                      placeholder="Enter the system prompt for this agent..."
                    />
                  </div>
                </TabsContent>

                <TabsContent value="model" className="space-y-6 pt-4">
                  <div className="space-y-2">
                    <Label htmlFor="modelId">AI Model</Label>
                    <select
                      id="modelId"
                      value={formData.modelId}
                      onChange={(e) => setFormData({ ...formData, modelId: e.target.value })}
                      className="w-full p-2 rounded border bg-background"
                    >
                      {AVAILABLE_MODELS.map((model) => (
                        <option key={model} value={model}>
                          {model}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="space-y-2">
                    <Label>Temperature: {formData.temperature}</Label>
                    <Slider
                      value={[formData.temperature]}
                      onValueChange={([value]) => setFormData({ ...formData, temperature: value })}
                      min={0}
                      max={2}
                      step={0.1}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="maxTokens">Max Tokens</Label>
                    <Input
                      id="maxTokens"
                      type="number"
                      value={formData.maxTokens}
                      onChange={(e) => setFormData({ ...formData, maxTokens: parseInt(e.target.value) })}
                    />
                  </div>
                </TabsContent>

                <TabsContent value="mcp" className="space-y-4 pt-4">
                  <div className="space-y-2">
                    <Label>MCP Servers</Label>
                    <p className="text-sm text-muted-foreground">
                      Add MCP server URLs that this agent can use for additional tools
                    </p>
                    <Textarea
                      value={formData.mcpServersConfig}
                      onChange={(e) => setFormData({ ...formData, mcpServersConfig: e.target.value })}
                      rows={5}
                      className="font-mono text-sm"
                      placeholder='["https://mcp.example.com/sse"]'
                    />
                    <div className="flex gap-2 mt-2">
                      <Badge variant="outline">Cloudflare Docs MCP (always enabled)</Badge>
                    </div>
                  </div>
                </TabsContent>

                <TabsContent value="constraints" className="space-y-4 pt-4">
                  <div className="space-y-2">
                    <Label>Agent Constraints (JSON)</Label>
                    <p className="text-sm text-muted-foreground">
                      Define specific constraints for this agent
                    </p>
                    <Textarea
                      value={formData.constraints}
                      onChange={(e) => setFormData({ ...formData, constraints: e.target.value })}
                      rows={10}
                      className="font-mono text-sm"
                      placeholder={`{
  "mustUseDrizzle": true,
  "preferredPatterns": ["repository pattern", "dependency injection"],
  "avoidPatterns": ["raw SQL", "any types"]
}`}
                    />
                  </div>
                </TabsContent>
              </Tabs>

              <div className="flex justify-end mt-6">
                <Button onClick={handleSave} disabled={updateConfig.isPending}>
                  <Save className="h-4 w-4 mr-2" />
                  Save Configuration
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
```

### 4.6 Future Features Roadmap Page

Create `apps/app/src/pages/FutureFeatures.tsx`:

```tsx
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { 
  Rocket, 
  GitPullRequest, 
  Bug, 
  Sparkles, 
  Layers, 
  Database,
  Globe,
  Shield,
  Zap,
  Users,
  BarChart,
  MessageSquare
} from 'lucide-react';

const features = [
  {
    category: 'Worker Management',
    icon: Layers,
    items: [
      { 
        title: 'Worker Version Management', 
        description: 'View and manage different versions of deployed workers, with rollback capabilities',
        status: 'planned' 
      },
      { 
        title: 'A/B Testing for Workers', 
        description: 'Split traffic between worker versions for gradual rollouts',
        status: 'planned' 
      },
      { 
        title: 'Worker Cloning', 
        description: 'Clone existing workers as templates for new projects',
        status: 'planned' 
      },
      { 
        title: 'Multi-Environment Support', 
        description: 'Manage dev, staging, and production environments for each worker',
        status: 'planned' 
      },
    ]
  },
  {
    category: 'Build & Deploy',
    icon: Rocket,
    items: [
      { 
        title: 'Parallel Task Execution', 
        description: 'Run independent build tasks in parallel for faster builds',
        status: 'in-progress' 
      },
      { 
        title: 'Build Caching', 
        description: 'Cache build artifacts to speed up subsequent builds',
        status: 'planned' 
      },
      { 
        title: 'Preview Deployments', 
        description: 'Automatic preview deployments for every PR',
        status: 'planned' 
      },
      { 
        title: 'Deployment Approval Workflows', 
        description: 'Require approvals before production deployments',
        status: 'planned' 
      },
    ]
  },
  {
    category: 'GitHub Integration',
    icon: GitPullRequest,
    items: [
      { 
        title: 'PR Code Review Analysis', 
        description: 'AI-powered analysis of PR code comments with automated fix suggestions',
        status: 'in-progress' 
      },
      { 
        title: 'Automated PR Fixes', 
        description: 'Clone PRs to sandbox, address code comments, and push fixes',
        status: 'planned' 
      },
      { 
        title: 'Issue-to-Worker Pipeline', 
        description: 'Create workers directly from GitHub issues',
        status: 'planned' 
      },
      { 
        title: 'Commit Message AI', 
        description: 'Auto-generate meaningful commit messages from code changes',
        status: 'planned' 
      },
    ]
  },
  {
    category: 'Debugging & Monitoring',
    icon: Bug,
    items: [
      { 
        title: 'Build Failure Analysis', 
        description: 'AI-powered analysis of build failures with automated fix PRs',
        status: 'in-progress' 
      },
      { 
        title: 'Runtime Error Detection', 
        description: 'Detect and alert on runtime errors in deployed workers',
        status: 'planned' 
      },
      { 
        title: 'Performance Profiling', 
        description: 'Analyze worker performance and suggest optimizations',
        status: 'planned' 
      },
      { 
        title: 'Log Aggregation', 
        description: 'Centralized logging with search and filtering',
        status: 'planned' 
      },
    ]
  },
  {
    category: 'AI Enhancements',
    icon: Sparkles,
    items: [
      { 
        title: 'Multi-Model Support', 
        description: 'Use different AI models for different agent tasks',
        status: 'planned' 
      },
      { 
        title: 'Context Window Optimization', 
        description: 'Intelligent context management for better code generation',
        status: 'planned' 
      },
      { 
        title: 'Learning from Feedback', 
        description: 'Improve agents based on user feedback and corrections',
        status: 'research' 
      },
      { 
        title: 'Custom Agent Training', 
        description: 'Fine-tune agents on organization-specific code patterns',
        status: 'research' 
      },
    ]
  },
  {
    category: 'Database & Storage',
    icon: Database,
    items: [
      { 
        title: 'Automatic Migration Generation', 
        description: 'Generate Drizzle migrations from schema changes',
        status: 'in-progress' 
      },
      { 
        title: 'Database Visualization', 
        description: 'Visual ERD diagrams for D1 schemas',
        status: 'planned' 
      },
      { 
        title: 'R2 Asset Management', 
        description: 'Upload and manage R2 assets through the UI',
        status: 'planned' 
      },
      { 
        title: 'Vectorize Integration', 
        description: 'Automatic vector index creation and management',
        status: 'planned' 
      },
    ]
  },
  {
    category: 'API & Integrations',
    icon: Globe,
    items: [
      { 
        title: 'OpenAPI Import', 
        description: 'Import existing OpenAPI specs to generate worker implementations',
        status: 'planned' 
      },
      { 
        title: 'GraphQL Support', 
        description: 'Generate GraphQL APIs alongside REST',
        status: 'planned' 
      },
      { 
        title: 'Third-Party MCP Marketplace', 
        description: 'Browse and connect to community MCP servers',
        status: 'planned' 
      },
      { 
        title: 'Webhook Management', 
        description: 'Create and manage webhooks for external integrations',
        status: 'planned' 
      },
    ]
  },
  {
    category: 'Security',
    icon: Shield,
    items: [
      { 
        title: 'Security Scanning', 
        description: 'Automatic security vulnerability scanning in generated code',
        status: 'planned' 
      },
      { 
        title: 'Secrets Management', 
        description: 'Secure management of API keys and secrets',
        status: 'planned' 
      },
      { 
        title: 'RBAC for Teams', 
        description: 'Role-based access control for team workspaces',
        status: 'planned' 
      },
      { 
        title: 'Audit Logging', 
        description: 'Comprehensive audit logs for all actions',
        status: 'planned' 
      },
    ]
  },
  {
    category: 'Performance',
    icon: Zap,
    items: [
      { 
        title: 'Smart Placement Optimization', 
        description: 'AI-powered Worker placement recommendations',
        status: 'planned' 
      },
      { 
        title: 'Bundle Size Analysis', 
        description: 'Analyze and optimize worker bundle sizes',
        status: 'planned' 
      },
      { 
        title: 'Cold Start Optimization', 
        description: 'Reduce cold start times with AI-suggested improvements',
        status: 'research' 
      },
    ]
  },
  {
    category: 'Collaboration',
    icon: Users,
    items: [
      { 
        title: 'Team Workspaces', 
        description: 'Shared workspaces for team collaboration',
        status: 'planned' 
      },
      { 
        title: 'Real-time Collaboration', 
        description: 'Multiple users viewing build progress simultaneously',
        status: 'in-progress' 
      },
      { 
        title: 'Comments & Discussions', 
        description: 'Comment on tasks and discuss implementation details',
        status: 'planned' 
      },
    ]
  },
  {
    category: 'Analytics',
    icon: BarChart,
    items: [
      { 
        title: 'Build Analytics Dashboard', 
        description: 'Track build times, success rates, and trends',
        status: 'planned' 
      },
      { 
        title: 'Agent Performance Metrics', 
        description: 'Monitor which agents perform best for different tasks',
        status: 'planned' 
      },
      { 
        title: 'Cost Estimation', 
        description: 'Estimate Cloudflare costs before deployment',
        status: 'planned' 
      },
    ]
  },
  {
    category: 'Chat & Canvas',
    icon: MessageSquare,
    items: [
      { 
        title: 'Chat Interface for Worker Design', 
        description: 'Conversational interface to design workers before building',
        status: 'planned' 
      },
      { 
        title: 'Visual Canvas Builder', 
        description: 'Drag-and-drop interface to design worker architecture',
        status: 'research' 
      },
      { 
        title: 'Canvas Export to CloudForge', 
        description: 'Export canvas designs to CloudForge via MCP',
        status: 'research' 
      },
    ]
  },
];

const statusColors = {
  'in-progress': 'bg-blue-500',
  'planned': 'bg-yellow-500',
  'research': 'bg-purple-500',
};

export function FutureFeatures() {
  return (
    <div className="container mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Feature Roadmap</h1>
        <p className="text-muted-foreground mt-1">
          Future features and capabilities planned for CloudForge
        </p>
      </div>

      <div className="grid gap-6">
        {features.map((category) => (
          <Card key={category.category}>
            <CardHeader>
              <div className="flex items-center gap-3">
                <category.icon className="h-6 w-6 text-primary" />
                <CardTitle>{category.category}</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-2 gap-4">
                {category.items.map((item) => (
                  <div 
                    key={item.title} 
                    className="p-4 rounded-lg border bg-card hover:bg-accent/50 transition-colors"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="font-medium">{item.title}</h3>
                        <p className="text-sm text-muted-foreground mt-1">
                          {item.description}
                        </p>
                      </div>
                      <Badge 
                        className={statusColors[item.status as keyof typeof statusColors]}
                      >
                        {item.status}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
```

## PHASE 5: IMPLEMENTATION NOTES

### 5.1 Key Implementation Requirements

1. **Sandbox SDK Version Sync**: Always match Docker image version to npm package version
2. **Drizzle Strict Mode**: Enable Drizzle strict mode for type safety
3. **All Bindings Named Consistently**: Use worker name for D1, KV, R2 binding names
4. **OpenAPI Operation IDs**: Every REST endpoint must have an operationId
5. **WebSocket Subscriptions**: Clean up subscriptions on disconnect
6. **MCP Server Registration**: Always register Cloudflare Docs MCP for documentation queries

### 5.2 Environment Variables Required

```bash
# Cloudflare
CLOUDFLARE_API_TOKEN=xxx
CLOUDFLARE_ACCOUNT_ID=xxx

# GitHub
GITHUB_TOKEN=xxx
GITHUB_ORG=your-org

# Database (for local Drizzle operations)
CLOUDFLARE_D1_DATABASE_ID=xxx
```

### 5.3 Commands to Run

```bash
# Initialize D1 database
wrangler d1 create cloudforge-db

# Create R2 bucket
wrangler r2 bucket create cloudforge-artifacts

# Create KV namespace
wrangler kv namespace create CACHE

# Generate Drizzle migrations
pnpm --filter @cloudforge/db drizzle:generate

# Push migrations to D1
pnpm --filter @cloudforge/db drizzle:push

# Deploy API worker
pnpm --filter cloudforge-api deploy

# Deploy App worker
pnpm --filter cloudforge-app deploy
```

### 5.4 Testing the Service

1. Create a new worker request via REST API:
```bash
curl -X POST https://cloudforge-api.workers.dev/api/v1/requests \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a simple API that tracks todo items with D1 database"}'
```

2. Subscribe to WebSocket for realtime updates
3. View progress in the frontend at https://cloudforge-app.workers.dev
4. Use MCP to create workers from AI chat interfaces

---

### 🧠 Knowledge & Research Protocol

**1. Preloaded Context (PRIORITY):**
I have preloaded your knowledge base with extensive documentation covering the **Cloudflare Sandbox SDK**, **Agents SDK**, **Drizzle/D1**, and **OpenAPI** patterns. You **MUST** reference this existing context first when designing the `BackendAgent`, `PlannerAgent`, and database schemas. Do not hallucinate APIs; verify against this provided knowledge.

**2. Active Research Tool (FALLBACK):**
If you encounter a knowledge gap, need to verify a specific API signature, or get stuck on a Cloudflare-specific error, you have access to a live RAG tool in the environment.
* **Command:** `pnpm exec tsx scripts/ask-cloudflare.ts "Your specific question here"`
* **When to use:** Use this *immediately* if you are unsure about a binding configuration, a specific SDK method, or a migration syntax. Do not guess—query the docs.

---

## SUMMARY

This comprehensive prompt provides everything needed to build CloudForge, an agentic Cloudflare Worker builder service with:

- **Multi-agent architecture** using Cloudflare Agents SDK
- **Sandbox SDK** for code execution with custom Dockerfile
- **Drizzle ORM** for D1 database management
- **Hono REST API** with OpenAPI 3.1.0 and Zod validation
- **WebSocket API** for realtime progress updates
- **MCP Server** for AI chat integration
- **React + shadcn frontend** with agent configuration UI
- **Backlog-style task tracking** with realtime status updates
- **GitHub integration** for repo creation and CI/CD setup
- **Comprehensive future features roadmap**

The service follows the monorepo structure (apps/api, apps/app) and uses consistent naming conventions for all Cloudflare resources.
