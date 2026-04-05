FROM node:20-alpine AS deps

WORKDIR /app

ENV HUSKY=0

COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci

FROM node:20-alpine AS builder

WORKDIR /app

ARG NEXT_PUBLIC_APP_NAME="FastAPI Template"
ARG NEXT_PUBLIC_API_URL="http://localhost:8000/api/v1"
ARG NEXT_PUBLIC_WS_URL="ws://localhost:8000"
ARG NEXT_PUBLIC_ANALYTICS_ENABLED="false"
ARG INTERNAL_API_BASE_URL="http://backend:8000"

ENV NODE_ENV=production \
    HUSKY=0 \
    NEXT_TELEMETRY_DISABLED=1 \
    NEXT_PUBLIC_APP_NAME=${NEXT_PUBLIC_APP_NAME} \
    NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL} \
    NEXT_PUBLIC_WS_URL=${NEXT_PUBLIC_WS_URL} \
    NEXT_PUBLIC_ANALYTICS_ENABLED=${NEXT_PUBLIC_ANALYTICS_ENABLED} \
    INTERNAL_API_BASE_URL=${INTERNAL_API_BASE_URL}

COPY --from=deps /app/node_modules ./node_modules
COPY package.json package-lock.json ./
COPY next.config.ts postcss.config.mjs tsconfig.json ./
COPY docker ./docker
COPY public ./public
COPY src ./src

RUN --mount=type=cache,target=/app/.next/cache \
    npm run build

FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/docker ./docker
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

CMD ["node", "server.js"]
