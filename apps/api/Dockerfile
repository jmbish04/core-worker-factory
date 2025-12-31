# CloudForge Custom Sandbox SDK Image
#
# CRITICAL: Version must match @cloudflare/sandbox npm package version
# Check package.json and update this base image version accordingly
# Current Tag: :0.4.0
FROM docker.io/cloudflare/sandbox:0.4.0

LABEL maintainer="CloudForge <cloudforge@hacolby.workers.dev>"
LABEL description="Custom sandbox environment for CloudForge worker building"
LABEL version="1.0.0"

# ============================================================================
# ENVIRONMENT CONFIGURATION
# ============================================================================
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    # Node/Bun Memory Limits
    NODE_OPTIONS="--max-old-space-size=4096" \
    # Path Configuration
    PNPM_HOME="/root/.local/share/pnpm" \
    BUN_INSTALL="/root/.bun" \
    # Python Module Path - Ensures 'import cloudforge' works globally
    PYTHONPATH="/opt/cloudforge:${PYTHONPATH}"

# Update PATH to include pnpm and bun
ENV PATH="${PNPM_HOME}:${BUN_INSTALL}/bin:${PATH}"

# ============================================================================
# SYSTEM DEPENDENCIES
# ============================================================================
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Version control & utilities
    git curl wget jq unzip \
    # GitHub CLI
    gh \
    # Build essentials (for native modules)
    build-essential python3-dev \
    # SQLite tools (for D1 debugging)
    sqlite3 \
    # Network tools (for debugging)
    dnsutils iputils-ping \
    # Process management & Text processing
    procps ripgrep \
    # Cleanup to reduce image size
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ============================================================================
# RUNTIME SETUP (Bun & Node)
# ============================================================================
# 1. Install Bun (Primary Runtime)
RUN curl -fsSL https://bun.sh/install | bash

# 2. Install pnpm (Package Manager)
RUN npm install -g pnpm@9

# 3. Install Global Tools
# We install these globally so Agents don't have to re-install them for every task
RUN npm install -g \
    # Cloudflare
    wrangler@latest \
    @cloudflare/workers-types@latest \
    # Database
    drizzle-kit@latest \
    # TypeScript / Runtime
    typescript@latest \
    tsx@latest \
    @types/bun@latest \
    @types/node@latest \
    # Build & Lint
    esbuild@latest \
    eslint@latest \
    prettier@latest \
    # Testing
    vitest@latest \
    # API
    @redocly/cli@latest

# ============================================================================
# PYTHON SETUP
# ============================================================================
# Upgrade pip
RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel

# 1. Install Dependencies (Cached Layer)
# We assume requirements.txt is located at scripts/requirements.txt relative to build context
COPY scripts/requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

# 2. Copy CloudForge Modules (Frequent Changes)
# This copies the content of 'scripts/' (including the 'cloudforge' package) to '/opt/cloudforge'
# Structure becomes:
#   /opt/cloudforge/cloudforge/ (package)
#   /opt/cloudforge/requirements.txt
#   /opt/cloudforge/setup_repo.py (standalone scripts)
COPY scripts/ /opt/cloudforge/

# ============================================================================
# CONFIGURATION
# ============================================================================
# Git Configuration
RUN git config --global user.email "cloudforge-bot@workers.dev" && \
    git config --global user.name "CloudForge Bot" && \
    git config --global init.defaultBranch main && \
    git config --global pull.rebase false && \
    git config --global core.autocrlf input && \
    git config --global credential.helper store

# Workspace Setup
RUN mkdir -p /workspace /tmp/cloudforge /var/log/cloudforge

WORKDIR /workspace

# ============================================================================
# HEALTHCHECK
# ============================================================================
# Verifies Python environment and that 'cloudforge' module is importable
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import cloudforge; print('healthy')" || exit 1

# Default command (sandbox SDK will override this)
CMD ["tail", "-f", "/dev/null"]
