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
