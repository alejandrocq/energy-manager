FROM node:22-alpine AS build-frontend
WORKDIR /app/client
COPY client/package.json client/package-lock.json ./
RUN npm install
COPY client/ ./
RUN npm run build

FROM python:3.13-slim
WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive
ARG TZ=UTC
ENV TZ=${TZ}

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      git tzdata postfix \
 && ln -sf /usr/share/zoneinfo/${TZ} /etc/localtime \
 && echo ${TZ} > /etc/timezone \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# copy built frontend into the image
COPY --from=build-frontend /app/client/dist ./client/dist

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
RUN adduser --disabled-password appuser && chown -R appuser /app /entrypoint.sh
USER appuser
ENTRYPOINT ["/entrypoint.sh"]

EXPOSE 8000
