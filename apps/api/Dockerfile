FROM node:20-alpine

RUN apk add --no-cache openssl openssl-dev

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
COPY apps/api/package.json apps/api/
COPY packages/db/package.json packages/db/
COPY packages/queue/package.json packages/queue/
COPY packages/storage/package.json packages/storage/

# Enable corepack and install dependencies
RUN corepack enable && pnpm install --no-frozen-lockfile && pnpm approve-builds --all

# Copy source code
COPY . .

# Rebuild to ensure all binaries are linked
RUN pnpm rebuild

# Build packages first, then the API
# Generate Prisma client at root, then build TypeScript directly
RUN pnpm exec prisma generate --schema=./packages/db/prisma/schema.prisma && \
    pnpm exec tsc --project packages/db/tsconfig.json && \
    pnpm exec tsc --project packages/queue/tsconfig.json && \
    pnpm exec tsc --project packages/storage/tsconfig.json && \
    pnpm exec tsc --project apps/api/tsconfig.json

EXPOSE 3000

CMD ["node", "apps/api/dist/index.js"]