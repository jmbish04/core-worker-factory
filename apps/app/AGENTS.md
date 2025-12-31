# AGENTS.md - CloudForge Frontend Worker

## Overview

The CloudForge Frontend (`apps/app`) is a React application built with shadcn/ui components, deployed as a Cloudflare Worker with static assets. It provides the user interface for creating workers, viewing build progress, configuring agents, and managing deployed workers.

## Directory Structure

```
apps/app/
├── AGENTS.md                 # This file
├── wrangler.jsonc            # Cloudflare Worker configuration
├── package.json              # Dependencies
├── tsconfig.json             # TypeScript configuration
├── vite.config.ts            # Vite configuration
├── tailwind.config.ts        # Tailwind CSS configuration
├── components.json           # shadcn/ui configuration
├── index.html                # HTML entry point
└── src/
    ├── main.tsx              # React entry point
    ├── App.tsx               # Root component with routing
    ├── index.css             # Global styles
    ├── components/           # Reusable UI components
    │   ├── ui/               # shadcn/ui components
    │   │   ├── button.tsx
    │   │   ├── card.tsx
    │   │   ├── badge.tsx
    │   │   └── ...
    │   ├── layout/           # Layout components
    │   │   ├── header.tsx
    │   │   ├── sidebar.tsx
    │   │   └── footer.tsx
    │   └── features/         # Feature-specific components
    │       ├── request-form.tsx
    │       ├── task-list.tsx
    │       ├── progress-bar.tsx
    │       └── agent-config-form.tsx
    ├── pages/                # Route pages
    │   ├── Dashboard.tsx
    │   ├── NewRequest.tsx
    │   ├── RequestDetails.tsx
    │   ├── WorkersList.tsx
    │   ├── WorkerDetails.tsx
    │   ├── AgentConfig.tsx
    │   └── FutureFeatures.tsx
    ├── hooks/                # Custom React hooks
    │   ├── use-toast.ts
    │   ├── use-api.ts
    │   └── use-debounce.ts
    ├── contexts/             # React contexts
    │   └── websocket.tsx     # WebSocket provider
    ├── lib/                  # Utilities
    │   ├── api.ts            # API client
    │   ├── utils.ts          # Helper functions
    │   └── constants.ts      # Constants
    └── types/                # TypeScript types
        └── index.ts          # Shared types
```

## Technology Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| React | 18.x | UI framework |
| TypeScript | 5.x | Type safety |
| Vite | 5.x | Build tool |
| React Router | 6.x | Client-side routing |
| TanStack Query | 5.x | Data fetching & caching |
| Tailwind CSS | 3.x | Utility-first CSS |
| shadcn/ui | latest | UI component library |
| Lucide React | latest | Icons |
| date-fns | latest | Date formatting |

## Wrangler Configuration

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

## Component Guidelines

### shadcn/ui Components

Always use shadcn/ui components for consistency:

```tsx
// ✅ Use shadcn/ui components
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

// ❌ Don't use raw HTML for UI elements
<button className="...">Click</button>  // Use <Button> instead
<div className="card">...</div>          // Use <Card> instead
```

### Adding New shadcn/ui Components

```bash
# Add new components via CLI
npx shadcn-ui@latest add dialog
npx shadcn-ui@latest add dropdown-menu
npx shadcn-ui@latest add select
```

### Component Structure

```tsx
// Standard component structure
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Loader2 } from 'lucide-react';
import { api } from '@/lib/api';
import type { Request } from '@/types';

interface RequestCardProps {
  requestId: string;
  onSelect?: (request: Request) => void;
}

export function RequestCard({ requestId, onSelect }: RequestCardProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['request', requestId],
    queryFn: () => api.getRequest(requestId),
  });

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-destructive">
        <CardContent className="py-4 text-destructive">
          Failed to load request
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="cursor-pointer hover:bg-accent/50 transition-colors"
          onClick={() => onSelect?.(data!)}>
      <CardHeader>
        <CardTitle>{data!.workerName}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-muted-foreground">{data!.prompt}</p>
      </CardContent>
    </Card>
  );
}
```

## State Management

### TanStack Query for Server State

```tsx
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';

// Fetching data
const { data, isLoading, error, refetch } = useQuery({
  queryKey: ['requests'],
  queryFn: api.listRequests,
  refetchInterval: 5000, // Fallback polling
});

// Mutations
const queryClient = useQueryClient();

const createRequest = useMutation({
  mutationFn: api.createRequest,
  onSuccess: (data) => {
    // Invalidate and refetch
    queryClient.invalidateQueries({ queryKey: ['requests'] });
    // Navigate to new request
    navigate(`/requests/${data.id}`);
  },
  onError: (error) => {
    toast({
      title: 'Error',
      description: error.message,
      variant: 'destructive',
    });
  },
});
```

### WebSocket Context for Realtime Updates

```tsx
// Context provider (src/contexts/websocket.tsx)
import { createContext, useContext, useEffect, useState, useCallback } from 'react';

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

export function WebSocketProvider({ url, children }: { url: string; children: ReactNode }) {
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState<WebSocketMessage[]>([]);
  // ... implementation
}

// Hook for subscribing to specific request
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

### Using Realtime Updates in Components

```tsx
import { useRequestUpdates } from '@/contexts/websocket';
import { useQuery } from '@tanstack/react-query';

export function TaskList({ requestId }: { requestId: string }) {
  // Fetch initial data
  const { data: request } = useQuery({
    queryKey: ['request', requestId],
    queryFn: () => api.getRequest(requestId),
  });

  // Get realtime updates
  const updates = useRequestUpdates(requestId);

  // Merge realtime updates with fetched data
  const tasks = request?.iterations?.[0]?.plans?.[0]?.tasks?.map((task) => {
    const update = updates.find(
      (u) => u.type === 'task_update' && u.data.taskId === task.id
    );
    return update ? { ...task, status: update.data.status } : task;
  }) || [];

  return (
    <div className="space-y-2">
      {tasks.map((task) => (
        <TaskItem key={task.id} task={task} />
      ))}
    </div>
  );
}
```

## API Client

```typescript
// src/lib/api.ts
const API_URL = import.meta.env.VITE_API_URL;

class ApiClient {
  private async fetch<T>(path: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: 'Request failed' }));
      throw new Error(error.message || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Requests
  async createRequest(data: CreateRequestInput) {
    return this.fetch<Request>('/api/v1/requests', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async listRequests(params?: { page?: number; status?: string }) {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.set('page', String(params.page));
    if (params?.status) searchParams.set('status', params.status);
    return this.fetch<PaginatedResponse<Request>>(`/api/v1/requests?${searchParams}`);
  }

  async getRequest(id: string) {
    return this.fetch<RequestWithDetails>(`/api/v1/requests/${id}`);
  }

  async modifyRequest(id: string, prompt: string) {
    return this.fetch<{ iterationId: string }>(`/api/v1/requests/${id}/modify`, {
      method: 'POST',
      body: JSON.stringify({ prompt }),
    });
  }

  // Workers
  async listWorkers() {
    return this.fetch<Worker[]>('/api/v1/workers');
  }

  async getWorker(name: string) {
    return this.fetch<WorkerDetails>(`/api/v1/workers/${name}`);
  }

  async fixWorkerBuild(name: string) {
    return this.fetch<{ message: string }>(`/api/v1/workers/${name}/fix`, {
      method: 'POST',
    });
  }

  // Agent Configurations
  async listAgentConfigs() {
    return this.fetch<AgentConfig[]>('/api/v1/agents/config');
  }

  async updateAgentConfig(name: string, config: Partial<AgentConfig>) {
    return this.fetch<AgentConfig>(`/api/v1/agents/config/${name}`, {
      method: 'PUT',
      body: JSON.stringify(config),
    });
  }
}

export const api = new ApiClient();
```

## Page Components

### Dashboard Page

```tsx
// src/pages/Dashboard.tsx
export function Dashboard() {
  const { data: requests } = useQuery({
    queryKey: ['requests', { limit: 10 }],
    queryFn: () => api.listRequests({ page: 1 }),
  });

  const { data: workers } = useQuery({
    queryKey: ['workers'],
    queryFn: api.listWorkers,
  });

  return (
    <div className="container mx-auto p-6 space-y-6">
      <h1 className="text-3xl font-bold">Dashboard</h1>
      
      {/* Stats Cards */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard title="Total Workers" value={workers?.length || 0} />
        <StatCard title="Active Builds" value={requests?.data.filter(r => r.status === 'IN_PROGRESS').length || 0} />
        <StatCard title="Completed" value={requests?.data.filter(r => r.status === 'COMPLETED').length || 0} />
        <StatCard title="Failed" value={requests?.data.filter(r => r.status === 'FAILED').length || 0} />
      </div>
      
      {/* Recent Requests */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Requests</CardTitle>
        </CardHeader>
        <CardContent>
          <RequestsTable requests={requests?.data || []} />
        </CardContent>
      </Card>
    </div>
  );
}
```

### New Request Page

```tsx
// src/pages/NewRequest.tsx
export function NewRequest() {
  const navigate = useNavigate();
  const { toast } = useToast();
  
  const createRequest = useMutation({
    mutationFn: api.createRequest,
    onSuccess: (data) => {
      toast({ title: 'Request created', description: `Building ${data.workerName}...` });
      navigate(`/requests/${data.id}`);
    },
  });

  const form = useForm<CreateRequestInput>({
    defaultValues: { prompt: '', workerName: '', githubRepoUrls: [] },
  });

  return (
    <div className="container mx-auto p-6 max-w-2xl">
      <h1 className="text-3xl font-bold mb-6">Create New Worker</h1>
      
      <Card>
        <CardContent className="pt-6">
          <form onSubmit={form.handleSubmit((data) => createRequest.mutate(data))} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="prompt">Describe your worker</Label>
              <Textarea
                id="prompt"
                {...form.register('prompt', { required: true, minLength: 10 })}
                placeholder="Create a REST API that tracks todo items with a D1 database..."
                rows={5}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="workerName">Worker name (optional)</Label>
              <Input
                id="workerName"
                {...form.register('workerName', { pattern: /^[a-z0-9-]*$/ })}
                placeholder="my-todo-api"
              />
            </div>
            
            <Button type="submit" className="w-full" disabled={createRequest.isPending}>
              {createRequest.isPending ? (
                <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Creating...</>
              ) : (
                'Create Worker'
              )}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
```

### Request Details Page (with Realtime Updates)

See the comprehensive example in the main prompt above for the full implementation with WebSocket subscriptions and realtime task status updates.

## Styling Guidelines

### Tailwind CSS Classes

```tsx
// Use Tailwind utility classes
<div className="container mx-auto p-6">
<div className="grid grid-cols-12 gap-6">
<div className="flex items-center justify-between">
<div className="space-y-4">

// Use hover and transition classes
<div className="hover:bg-accent/50 transition-colors">

// Dark mode support (automatic via ThemeProvider)
<div className="bg-background text-foreground">
<div className="border-border">
```

### CSS Variables (shadcn/ui theme)

```css
/* src/index.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --card: 0 0% 100%;
    --card-foreground: 222.2 84% 4.9%;
    --primary: 222.2 47.4% 11.2%;
    --primary-foreground: 210 40% 98%;
    --secondary: 210 40% 96.1%;
    --secondary-foreground: 222.2 47.4% 11.2%;
    --muted: 210 40% 96.1%;
    --muted-foreground: 215.4 16.3% 46.9%;
    --accent: 210 40% 96.1%;
    --accent-foreground: 222.2 47.4% 11.2%;
    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 210 40% 98%;
    --border: 214.3 31.8% 91.4%;
    --ring: 222.2 84% 4.9%;
    --radius: 0.5rem;
  }

  .dark {
    --background: 222.2 84% 4.9%;
    --foreground: 210 40% 98%;
    /* ... dark mode values */
  }
}
```

### Status Badge Colors

```tsx
const statusColors: Record<string, string> = {
  TODO: 'bg-gray-500',
  IN_PROGRESS: 'bg-blue-500 animate-pulse',
  PENDING_PEER_REVIEW: 'bg-yellow-500',
  IN_REVIEW: 'bg-purple-500',
  BLOCKED: 'bg-red-500',
  COMPLETED: 'bg-green-500',
  FAILED: 'bg-red-600',
};

// Usage
<Badge className={statusColors[task.status]}>
  {task.status.replace(/_/g, ' ')}
</Badge>
```

## Routing

```tsx
// src/App.tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/requests/new" element={<NewRequest />} />
        <Route path="/requests/:id" element={<RequestDetails />} />
        <Route path="/workers" element={<WorkersList />} />
        <Route path="/workers/:name" element={<WorkerDetails />} />
        <Route path="/agents/config" element={<AgentConfig />} />
        <Route path="/roadmap" element={<FutureFeatures />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  );
}
```

## Error Handling

### Error Boundary

```tsx
// src/components/error-boundary.tsx
import { Component, ErrorInfo, ReactNode } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { AlertTriangle } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Error boundary caught:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <Card className="m-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-destructive">
              <AlertTriangle className="h-5 w-5" />
              Something went wrong
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground mb-4">
              {this.state.error?.message || 'An unexpected error occurred'}
            </p>
            <Button onClick={() => window.location.reload()}>
              Reload Page
            </Button>
          </CardContent>
        </Card>
      );
    }

    return this.props.children;
  }
}
```

### Toast Notifications

```tsx
import { useToast } from '@/hooks/use-toast';

function MyComponent() {
  const { toast } = useToast();

  const handleAction = async () => {
    try {
      await doSomething();
      toast({
        title: 'Success',
        description: 'Action completed successfully',
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: error.message,
        variant: 'destructive',
      });
    }
  };
}
```

## Testing

### Component Tests

```tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { NewRequest } from '@/pages/NewRequest';

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

const wrapper = ({ children }) => (
  <QueryClientProvider client={queryClient}>
    <BrowserRouter>{children}</BrowserRouter>
  </QueryClientProvider>
);

describe('NewRequest', () => {
  it('should render the form', () => {
    render(<NewRequest />, { wrapper });
    expect(screen.getByLabelText(/describe your worker/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /create worker/i })).toBeInTheDocument();
  });

  it('should submit the form', async () => {
    render(<NewRequest />, { wrapper });
    
    fireEvent.change(screen.getByLabelText(/describe your worker/i), {
      target: { value: 'Create a todo API with D1 database' },
    });
    
    fireEvent.click(screen.getByRole('button', { name: /create worker/i }));
    
    // Assert loading state, then success
  });
});
```

### Hook Tests

```tsx
import { renderHook, waitFor } from '@testing-library/react';
import { useRequestUpdates } from '@/contexts/websocket';

describe('useRequestUpdates', () => {
  it('should filter messages by requestId', async () => {
    const { result } = renderHook(() => useRequestUpdates('req_123'), {
      wrapper: WebSocketProvider,
    });

    await waitFor(() => {
      expect(result.current).toEqual([]);
    });
  });
});
```

## Build & Deployment

### Build Commands

```bash
# Development
pnpm dev                  # Start Vite dev server
pnpm dev:remote           # Dev with remote API

# Build
pnpm build                # Build for production
pnpm preview              # Preview production build

# Deploy
pnpm deploy               # Deploy to Cloudflare Workers
```

### Environment Variables

```bash
# .env.development
VITE_API_URL=http://localhost:8787

# .env.production
VITE_API_URL=https://cloudforge-api.workers.dev
```

### Vite Configuration

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
});
```

## Accessibility

### Guidelines

1. Use semantic HTML elements
2. Include proper ARIA labels
3. Ensure keyboard navigation
4. Maintain color contrast ratios
5. Provide loading states

```tsx
// Good accessibility practices
<Button aria-label="Create new worker request">
  <Plus className="h-4 w-4" aria-hidden="true" />
  <span>New Request</span>
</Button>

<Input
  id="prompt"
  aria-describedby="prompt-description"
  aria-required="true"
/>
<p id="prompt-description" className="text-sm text-muted-foreground">
  Describe what you want your worker to do
</p>

// Loading states
{isLoading ? (
  <div role="status" aria-live="polite">
    <Loader2 className="h-6 w-6 animate-spin" />
    <span className="sr-only">Loading...</span>
  </div>
) : (
  <Content />
)}
```

---

For backend development guidance, see [../api/AGENTS.md](../api/AGENTS.md)
