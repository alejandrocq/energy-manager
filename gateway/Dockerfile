FROM nginx:alpine

# Create non-root user with UID/GID 500
RUN addgroup -g 500 appgroup && \
    adduser -u 500 -G appgroup -s /bin/sh -D appuser

# Create necessary directories and set permissions
RUN mkdir -p /var/cache/nginx /var/log/nginx /run && \
    chown -R appuser:appgroup /var/cache/nginx /var/log/nginx /etc/nginx /run

# Change nginx to run on port 8080 (non-privileged port)
RUN sed -i 's/listen\s*80;/listen 8080;/' /etc/nginx/conf.d/default.conf || true

USER appuser

EXPOSE 8080
