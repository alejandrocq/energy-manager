FROM node:22-alpine as build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM node:22-alpine
WORKDIR /app

# Create non-root user with UID/GID 500
RUN addgroup -g 500 appgroup && \
    adduser -u 500 -G appgroup -s /bin/sh -D appuser

COPY --from=build --chown=appuser:appgroup /app/dist /app/dist
RUN npm install -g serve && \
    chown -R appuser:appgroup /app

USER appuser

EXPOSE 3000
CMD ["serve", "-s", "dist", "-l", "3000"]
