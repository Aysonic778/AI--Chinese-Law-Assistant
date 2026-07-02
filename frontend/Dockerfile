FROM node:22-alpine AS deps
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY frontend .
ENV BACKEND_URL=http://backend:8000
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV BACKEND_URL=http://backend:8000
ENV NEXT_PUBLIC_API_URL=
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["npm", "run", "start", "--", "-H", "0.0.0.0", "-p", "3000"]
