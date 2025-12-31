# AGENTS.md - CloudForge API Worker

## Overview

The CloudForge API Worker (`apps/api`) is the backend service that orchestrates the multi-agent system, handles REST/WebSocket/MCP APIs, and manages code execution in Sandbox SDK containers.

## Directory Structure

```
apps/api/
├── AGENTS.md                 # This file
├── Dockerfile                # Custom Sandbox SDK image
├── wrangler.jsonc            # Cloudflare Worker configuration
├── package.json              # Dependencies
├── tsconfig.json             # TypeScript configuration
└── src/
    ├── index.ts              # Main entry point & Hono app
    ├── agents/               # Agent class definitions
    │   ├── orchestrator.ts   # Orchestrator Agent
    │   ├── planner.ts        # Planning Agent
    │   ├── backend.ts        # Backend Development Agent
    │   ├── ux.ts             # UX/Frontend Agent
    │   ├── data-engineer.ts  # Data Engineering Agent
    │   ├── api.ts            # API Design Agent
    │   ├── documentation.ts  # Documentation Agent
    │   └── qa.ts             # QA/Testing Agent
    ├── routes/               # Hono API routes
    │   ├── requests.ts       # /api/v1/requests/*
    │   ├── workers.ts        # /api/v1/workers/*
    │   ├── agents.ts         # /api/v1/agents/*
    │   └── progress.ts       # /api/v1/progress/*
    ├── mcp/                   # MCP server implementation
    │   └── server.ts         # CloudForge MCP Server
    ├── websocket/            # WebSocket handlers
    │   └── handler.ts        # WebSocket connection manager
    └── lib/                  # Utilities
        ├── cloudflare-api.ts # Cloudflare API wrapper
        ├── github-api.ts     # GitHub API wrapper
        └── broadcast.ts      # WebSocket broadcast utilities
```

## Bindings Configuration

The API worker requires these Cloudflare bindings in `wrangler.jsonc`:

```jsonc
{
  // D1 Database
  "d1_databases": [{
    "binding": "DB",
    "database_name": "cloudforge-db",
    "database_id": "<YOUR_D1_ID>"
  }],
  
  // R2 Storage
  "r2_buckets": [{
    "binding": "ARTIFACTS",
    "bucket_name": "cloudforge-artifacts"
  }],
  
  // KV Cache
  "kv_namespaces": [{
    "binding": "CACHE",
    "id": "<YOUR_KV_ID>"
  }],
  
  // Workers AI
  "ai": { "binding": "AI" },
  
  // Sandbox Container
  "containers": [{
    "class_name": "Sandbox",
    "image": "./Dockerfile",
    "max_instances": 10
  }],
  
  // Durable Objects (Agents)
  "durable_objects": {
    "bindings": [
      { "class_name": "Sandbox", "name": "Sandbox" },
      { "class_name": "OrchestratorAgent", "name": "ORCHESTRATOR" },
      { "class_name": "PlannerAgent", "name": "PLANNER" },
      { "class_name": "BackendAgent", "name": "BACKEND" },
      { "class_name": "UXAgent", "name": "UX" },
      { "class_name": "DataEngineerAgent", "name": "DATA_ENGINEER" },
      { "class_name": "APIAgent", "name": "API" },
      { "class_name": "DocumentationAgent", "name": "DOCUMENTATION" },
      { "class_name": "QAAgent", "name": "QA" }
    ]
  }
}
```

## Agent Implementation Guide

### Base Agent Structure

Every agent extends the `Agent` class from the Cloudflare Agents SDK:

```typescript
import { Agent } from 'agents';
import { drizzle } from 'drizzle-orm/d1';
import * as schema from '@cloudforge/db/schema';
import { broadcastUpdate } from '../websocket/handler';

interface MyAgentState {
  requestId: string;
  currentTaskId: string | null;
}

export class MyAgent extends Agent<Env, MyAgentState> {
  private db: ReturnType<typeof drizzle>;
  
  // Called once when agent is created
  async onStart() {
    this.db = drizzle(this.env.DB, { schema });
  }
  
  // Handle incoming requests from other agents
  async onRequest(request: Request): Promise<Response> {
    const url = new URL(request.url);
    
    switch (url.pathname) {
      case '/assign-tasks':
        const body = await request.json();
        await this.processTasks(body);
        return new Response(JSON.stringify({ status: 'ok' }));
      
      default:
        return new Response('Not found', { status: 404 });
    }
  }
  
  // Optional: Handle WebSocket connections
  async onConnect(connection: Connection) {
    // Handle realtime communication
  }
  
  private async processTasks(params: TaskParams) {
    // Implementation
  }
}
```

### Agent Responsibilities

#### OrchestratorAgent
- **Purpose**: Coordinates the entire build process
- **Key Methods**:
  - `startBuildProcess(requestId)` - Initiates new worker build
  - `startModificationProcess(requestId, prompt)` - Handles modifications
  - `generateDocsQueries(prompt)` - Creates Cloudflare docs search queries
  - `loadCloudflareDocsContext(queries)` - Fetches documentation via MCP
  - `onTaskCompleted(taskId)` - Handles task completion events
  - `progressToNextPhase(requestId)` - Advances build phase

```typescript
// Orchestrator coordinates via MCP and Durable Object calls
async startBuildProcess(requestId: string) {
  // 1. Generate documentation queries
  const docsQueries = await this.generateDocsQueries(request.prompt);
  
  // 2. Load Cloudflare docs context via MCP
  await this.addMcpServer('cloudflare-docs', 'https://developers.cloudflare.com/mcp');
  const docsContext = await this.loadCloudflareDocsContext(docsQueries);
  
  // 3. Delegate to Planner Agent
  const plannerId = this.env.PLANNER.idFromName(requestId);
  const planner = this.env.PLANNER.get(plannerId);
  await planner.fetch(new Request('http://internal/create-plan', {
    method: 'POST',
    body: JSON.stringify({ requestId, prompt, docsContext }),
  }));
}
```

#### PlannerAgent
- **Purpose**: Creates detailed build plans and assigns tasks
- **Key Methods**:
  - `createPlan(params)` - Generates comprehensive build plan
  - `dispatchTasks(tasks)` - Assigns tasks to appropriate agents
  - `topologicalSort(tasks)` - Orders tasks by dependencies

```typescript
// Plan generation with AI
const planResponse = await this.env.AI.run('@cf/meta/llama-3.1-70b-instruct', {
  messages: [
    { role: 'system', content: systemPrompt },
    { role: 'user', content: `Create plan for: ${prompt}` },
  ],
});

// Expected plan structure
interface Plan {
  summary: string;
  architecture: {
    components: string[];
    bindings: ('D1' | 'R2' | 'KV' | 'AI' | 'Vectorize')[];
    frameworks: string[];
  };
  tasks: {
    title: string;
    description: string;
    assignedAgent: AgentName;
    priority: number;
    estimatedComplexity: 'LOW' | 'MEDIUM' | 'HIGH';
    dependencies: string[];
  }[];
}
```

#### BackendAgent
- **Purpose**: Implements server-side Worker code
- **Key Methods**:
  - `processTasks(tasks)` - Executes backend development tasks
  - `createNewWorkerRepo(sandbox, workerName)` - Forks starter kit
  - `executeTask(sandbox, task)` - Generates and applies code

```typescript
// Code generation and sandbox execution
const sandbox = getSandbox(this.env.Sandbox, `backend-${requestId}`);

// Fork starter kit
await this.createNewWorkerRepo(sandbox, workerName, requestId);

// Generate code with AI
const codeResponse = await this.env.AI.run(modelId, {
  messages: [{ role: 'system', content: systemPrompt }, { role: 'user', content: taskPrompt }],
});

// Apply changes in sandbox
for (const file of codeChanges.files) {
  await sandbox.writeFile(`/workspace/${workerName}/${file.path}`, file.content);
}

// Commit and push
await sandbox.exec(`cd /workspace/${workerName} && git add -A && git commit -m "${task.title}" && git push`);
```

#### DataEngineerAgent
- **Purpose**: Designs database schemas and manages migrations
- **Key Methods**:
  - `processTasks(tasks)` - Executes data engineering tasks
  - `createBindings(workerName, bindings)` - Creates D1/R2/KV resources
  - `generateDrizzleSchema(requirements)` - Creates Drizzle schema

```typescript
// Schema generation rules
const schemaRules = `
- Use drizzle-orm/sqlite-core for D1
- Primary keys: text with cuid2
- Include created_at/updated_at timestamps
- Use snake_case column names
- Define explicit foreign key relations
- Add indexes for frequently queried columns
`;

// Create D1 database via Cloudflare API
const cloudflare = new Cloudflare({ apiToken: this.env.CLOUDFLARE_API_TOKEN });
const database = await cloudflare.d1.database.create({
  account_id: this.env.CLOUDFLARE_ACCOUNT_ID,
  name: `${workerName}-db`,
});
```

#### UXAgent
- **Purpose**: Builds React frontend components
- **Key Methods**:
  - `processTasks(tasks)` - Executes frontend development tasks
  - `generateComponent(requirements)` - Creates React components
  - `applyStyles(component)` - Adds Tailwind/shadcn styling

```typescript
// Frontend generation rules
const frontendRules = `
- Use React with TypeScript
- Use shadcn/ui components
- Use Tailwind CSS for styling
- Use TanStack Query for data fetching
- Use React Router for navigation
- Follow the apps/app structure
`;
```

#### APIAgent
- **Purpose**: Designs REST/WebSocket/MCP APIs
- **Key Methods**:
  - `processTasks(tasks)` - Executes API design tasks
  - `generateOpenAPISpec(requirements)` - Creates OpenAPI 3.1.0 spec
  - `generateHonoRoutes(spec)` - Implements Hono routes

```typescript
// OpenAPI requirements
const openAPIRules = `
- OpenAPI version: 3.1.0
- Every endpoint MUST have operationId
- Use Zod schemas with .openapi() for validation
- Include request/response examples
- Document error responses
- Serve spec at /openapi.json, /openapi.yaml, /swagger
`;
```

#### DocumentationAgent
- **Purpose**: Generates documentation
- **Key Methods**:
  - `processTasks(tasks)` - Executes documentation tasks
  - `generateREADME(project)` - Creates README.md
  - `generateAPIDoc(openAPISpec)` - Creates API documentation

#### QAAgent
- **Purpose**: Testing, validation, and build fixes
- **Key Methods**:
  - `processTasks(tasks)` - Executes QA tasks
  - `analyzeBuildFailure(logs)` - Diagnoses build errors
  - `createFixPR(analysis)` - Creates PR with fixes
  - `reviewPRComments(pr)` - Analyzes PR code comments

```typescript
// Build failure analysis
async analyzeBuildFailure(workerName: string, buildLogs: string) {
  const analysis = await this.env.AI.run(modelId, {
    messages: [{
      role: 'system',
      content: 'Analyze this build failure and provide a fix',
    }, {
      role: 'user',
      content: buildLogs,
    }],
  });
  
  // Clone to sandbox and apply fix
  const sandbox = getSandbox(this.env.Sandbox, `qa-fix-${workerName}`);
  await sandbox.gitCheckout(repoUrl);
  // Apply fixes...
  // Create PR with fix
}
```

## REST API Design

### Route Structure

All routes use Hono with Zod OpenAPI:

```typescript
import { OpenAPIHono, createRoute, z } from '@hono/zod-openapi';

const app = new OpenAPIHono<{ Bindings: Env }>();

// Define schema
const RequestSchema = z.object({
  prompt: z.string().min(10),
  workerName: z.string().regex(/^[a-z0-9-]+$/).optional(),
}).openapi('CreateRequestInput');

// Define route with operationId (REQUIRED)
const createRoute = createRoute({
  method: 'post',
  path: '/',
  operationId: 'createRequest',  // ← MUST HAVE
  tags: ['Requests'],
  summary: 'Create a new worker build request',
  request: {
    body: { content: { 'application/json': { schema: RequestSchema } } },
  },
  responses: {
    201: { description: 'Created', content: { 'application/json': { schema: ResponseSchema } } },
    400: { description: 'Validation error' },
  },
});

// Implement handler
app.openapi(createRoute, async (c) => {
  const body = c.req.valid('json');
  // Implementation...
  return c.json(result, 201);
});
```

### API Endpoints

| Method | Path | operationId | Description |
|--------|------|-------------|-------------|
| POST | /api/v1/requests | createRequest | Create new worker build |
| GET | /api/v1/requests | listRequests | List all requests |
| GET | /api/v1/requests/:id | getRequest | Get request details |
| POST | /api/v1/requests/:id/modify | modifyWorker | Modify existing worker |
| GET | /api/v1/workers | listWorkers | List all workers |
| GET | /api/v1/workers/:name | getWorker | Get worker details |
| GET | /api/v1/workers/:name/builds | getWorkerBuilds | Get build history |
| POST | /api/v1/workers/:name/fix | fixWorkerBuild | Fix failed build |
| GET | /api/v1/agents/config | listAgentConfigs | List agent configurations |
| PUT | /api/v1/agents/config/:name | updateAgentConfig | Update agent config |
| GET | /api/v1/progress/:requestId | getProgress | Get build progress |
| GET | /openapi.json | getOpenAPIJSON | OpenAPI spec (JSON) |
| GET | /openapi.yaml | getOpenAPIYAML | OpenAPI spec (YAML) |
| GET | /swagger | swaggerUI | Swagger UI |
| WS | /ws | - | WebSocket endpoint |
| * | /mcp/* | - | MCP server endpoints |

## WebSocket Protocol

### Connection
```javascript
const ws = new WebSocket('wss://cloudforge-api.workers.dev/ws');
```

### Client Messages
```typescript
// Subscribe to request updates
{ "type": "subscribe", "requestId": "req_xxx" }

// Unsubscribe
{ "type": "unsubscribe", "requestId": "req_xxx" }

// Ping/keepalive
{ "type": "ping" }
```

### Server Messages
```typescript
// Task status update
{
  "type": "task_update",
  "requestId": "req_xxx",
  "data": {
    "taskId": "task_xxx",
    "status": "IN_PROGRESS" | "PENDING_PEER_REVIEW" | "COMPLETED" | "FAILED"
  },
  "timestamp": "2025-01-15T10:30:00Z"
}

// Request status update
{
  "type": "request_update",
  "requestId": "req_xxx",
  "data": { "status": "PLANNING" | "IN_PROGRESS" | "COMPLETED" },
  "timestamp": "2025-01-15T10:30:00Z"
}

// Plan created
{
  "type": "plan_created",
  "requestId": "req_xxx",
  "data": { "planId": "plan_xxx", "taskCount": 12 },
  "timestamp": "2025-01-15T10:30:00Z"
}

// Agent activity
{
  "type": "agent_activity",
  "requestId": "req_xxx",
  "data": { "agent": "BACKEND", "action": "generating_code" },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

## MCP Server Implementation

The API exposes an MCP server for AI chat integration:

```typescript
import { McpAgent } from 'agents/mcp';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp';

export class CloudForgeMCPServer extends McpAgent {
  server = new McpServer({ name: 'CloudForge', version: '1.0.0' });

  async init() {
    // Tool: Create worker
    this.server.tool('create_worker', 'Create a new Cloudflare Worker', {
      prompt: z.string(),
      workerName: z.string().optional(),
    }, async ({ prompt, workerName }) => {
      // Implementation
    });

    // Tool: Modify worker
    this.server.tool('modify_worker', 'Modify existing worker', {
      workerName: z.string(),
      prompt: z.string(),
    }, async (params) => {
      // Implementation
    });

    // Tool: List workers
    this.server.tool('list_workers', 'List all workers', {}, async () => {
      // Implementation
    });

    // Tool: Get progress
    this.server.tool('get_request_progress', 'Get build progress', {
      requestId: z.string(),
    }, async ({ requestId }) => {
      // Implementation
    });

    // Tool: Fix build failure
    this.server.tool('fix_build_failure', 'Fix failed build', {
      workerName: z.string(),
    }, async ({ workerName }) => {
      // Implementation
    });

    // Resource: Request details
    this.server.resource('request', 'cloudforge://request/{id}', async (uri) => {
      // Implementation
    });
  }
}
```

## Sandbox SDK Usage

### Custom Dockerfile

```dockerfile
FROM docker.io/cloudflare/sandbox:0.3.3

# System dependencies
RUN apt-get update && apt-get install -y \
    git curl jq gh \
    && rm -rf /var/lib/apt/lists/*

# Python packages for automation
RUN pip install --no-cache-dir \
    cloudflare PyGithub gitpython requests pyyaml toml

# Node.js global packages
RUN npm install -g wrangler @cloudflare/workers-types drizzle-kit typescript tsx

# Git configuration
RUN git config --global user.email "cloudforge@workers.dev" && \
    git config --global user.name "CloudForge Bot"

WORKDIR /workspace
```

### Sandbox Operations

```typescript
import { getSandbox } from '@cloudflare/sandbox';

// Get sandbox instance (use consistent ID per request)
const sandbox = getSandbox(env.Sandbox, `backend-${requestId}`);

// Clone repository
await sandbox.gitCheckout('https://github.com/org/repo', {
  branch: 'main',
  depth: 1,
});

// Execute commands
const result = await sandbox.exec('npm install');
console.log(result.stdout, result.stderr);

// File operations
await sandbox.writeFile('/workspace/file.ts', content);
const fileContent = await sandbox.readFile('/workspace/file.ts');
await sandbox.deleteFile('/workspace/old-file.ts');

// Create directories
await sandbox.exec('mkdir -p /workspace/src/components');

// Commit and push
await sandbox.exec(`
  cd /workspace/my-worker &&
  git add -A &&
  git commit -m "feat: Add new feature" &&
  git push
`);

// Create code context for Python execution
const pythonCtx = await sandbox.createCodeContext({ language: 'python' });
const result = await pythonCtx.execute('print("Hello from Python")');
```

## Testing

### Unit Tests
```typescript
import { unstable_dev } from 'wrangler';

describe('API Routes', () => {
  let worker: UnstableDevWorker;

  beforeAll(async () => {
    worker = await unstable_dev('src/index.ts', {
      experimental: { disableExperimentalWarning: true },
    });
  });

  afterAll(async () => {
    await worker.stop();
  });

  it('should create a request', async () => {
    const response = await worker.fetch('/api/v1/requests', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt: 'Create a todo API' }),
    });
    expect(response.status).toBe(201);
  });
});
```

### Agent Tests
```typescript
import { env } from 'cloudflare:test';

describe('OrchestratorAgent', () => {
  it('should generate documentation queries', async () => {
    const orchestratorId = env.ORCHESTRATOR.idFromName('test-request');
    const orchestrator = env.ORCHESTRATOR.get(orchestratorId);
    
    const response = await orchestrator.fetch(new Request('http://internal/start', {
      method: 'POST',
      body: JSON.stringify({ requestId: 'test-request' }),
    }));
    
    expect(response.status).toBe(200);
  });
});
```

## Deployment

```bash
# Deploy to production
pnpm --filter cloudforge-api deploy

# Deploy to staging
pnpm --filter cloudforge-api deploy --env staging

# View logs
wrangler tail cloudforge-api

# Run migrations before deploy
pnpm --filter @cloudforge/db push
```

## Debugging

### Enable Debug Logging
```typescript
// In agent code
if (this.env.ENABLE_DEBUG_LOGGING === 'true') {
  console.log('[DEBUG]', JSON.stringify({ action, data }));
}
```

### View Durable Object State
```bash
# Get DO state via wrangler
wrangler durable-object get ORCHESTRATOR req_xxx
```

### Sandbox Debugging
```typescript
// Get sandbox logs
const logs = await sandbox.exec('cat /var/log/build.log');
console.log('Build logs:', logs.stdout);

// Interactive debugging (local only)
const sandbox = getSandbox(env.Sandbox, 'debug-session', { keepAlive: 600 });
```

---

For frontend development guidance, see [../app/AGENTS.md](../app/AGENTS.md)
