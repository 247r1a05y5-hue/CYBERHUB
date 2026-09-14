# ── CyberHub Frontend (React Web Service) ──────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Accept build argument for dynamic API URL if baked in at build time
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# Copy source code and build production bundle
COPY . .
RUN npm run build

# ── Production Nginx Stage ──────────────────────────────────────────────────
FROM nginx:alpine AS production

# Copy compiled static assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy dynamic port template (Nginx automatically evaluates /etc/nginx/templates/*.template with env vars like $PORT)
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

ENV PORT=80

EXPOSE 80

HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1:${PORT:-80}/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
