FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
COPY travel-api/package.json ./travel-api/package.json
COPY travel-web/package.json ./travel-web/package.json
COPY packages/contracts/package.json ./packages/contracts/package.json
RUN npm ci
COPY packages/contracts ./packages/contracts
COPY travel-api ./travel-api
RUN npm run build -w @travel-growth-inspiration/contracts && npm run build -w travel-nova-api

FROM node:22-alpine AS runtime
ENV NODE_ENV=production
ENV DATABASE_PATH=/app/data/travel-nova.sqlite
WORKDIR /app
COPY package.json package-lock.json ./
COPY travel-api/package.json ./travel-api/package.json
COPY travel-web/package.json ./travel-web/package.json
COPY packages/contracts/package.json ./packages/contracts/package.json
RUN npm ci --omit=dev
COPY --from=build /app/packages/contracts/dist ./packages/contracts/dist
COPY --from=build /app/travel-api/dist ./travel-api/dist
RUN mkdir -p /app/data && chown -R node:node /app/data
USER node
EXPOSE 3000
CMD ["node", "travel-api/dist/server.js"]
