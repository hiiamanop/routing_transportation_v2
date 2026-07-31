FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:20-alpine AS builder
WORKDIR /app
# next.config.ts rewrites() di-bake ke .next/routes-manifest.json saat BUILD
# (next start membaca manifest itu, tidak memanggil rewrites() lagi) -- jadi
# API_INTERNAL_URL wajib ada di sini, bukan cuma sbg ENV runtime di stage runner.
ARG API_INTERNAL_URL=http://localhost:5001
ENV API_INTERNAL_URL=$API_INTERNAL_URL
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/next.config.ts ./next.config.ts

EXPOSE 3000

CMD ["npm", "start"]
