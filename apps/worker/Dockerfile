FROM node:20-bookworm

# Install system dependencies for conversion tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    pandoc \
    imagemagick \
    ghostscript \
    libvips-dev \
    ffmpeg \
    libreoffice \
    && rm -rf /var/lib/apt/lists/*

# Allow ImageMagick to write PDF output (denied by default in Debian)
RUN sed -i \
    -e 's/<policy domain="coder" rights="none" pattern="PDF"/<policy domain="coder" rights="read|write" pattern="PDF"/' \
    -e 's/<policy domain="coder" rights="none" pattern="EPS"/<policy domain="coder" rights="read|write" pattern="EPS"/' \
    -e 's/<policy domain="coder" rights="none" pattern="PS"/<policy domain="coder" rights="read|write" pattern="PS"/' \
    /etc/ImageMagick-6/policy.xml

WORKDIR /app

# Set CI mode early to avoid interactive prompts
ENV CI=true
ENV PNPM_NO_TTY=1

# Copy .npmrc for script settings
COPY .npmrc .

# Copy workspace files first for better layer caching
COPY pnpm-workspace.yaml .
COPY package.json .
COPY tsconfig.base.json .
COPY apps/worker/package.json apps/worker/
COPY packages/db/package.json packages/db/
COPY packages/queue/package.json packages/queue/
COPY packages/storage/package.json packages/storage/
COPY packages/shared/package.json packages/shared/

# Enable corepack and install dependencies
RUN corepack enable && pnpm install --no-frozen-lockfile && pnpm approve-builds --all

# Copy source code
COPY . .

# Rebuild to ensure all binaries are linked
RUN pnpm rebuild

# Build packages first, then the worker
# Generate Prisma client at root, then build TypeScript directly
RUN pnpm exec prisma generate --schema=./packages/db/prisma/schema.prisma && \
    pnpm exec tsc --project packages/db/tsconfig.json && \
    pnpm exec tsc --project packages/queue/tsconfig.json && \
    pnpm exec tsc --project packages/storage/tsconfig.json && \
    pnpm exec tsc --project apps/worker/tsconfig.json

CMD ["node", "apps/worker/dist/index.js"]