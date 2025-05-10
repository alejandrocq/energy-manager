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

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      gosu git tzdata postfix \
 && ln -sf /usr/share/zoneinfo/${TZ} /etc/localtime \
 && echo ${TZ} > /etc/timezone \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# copy built frontend into the image
COPY --from=build-frontend /app/client/dist ./client/dist

COPY entrypoint.sh /entrypoint.sh

ARG USER_ID=1000
RUN useradd -u ${USER_ID} -m appuser && \
    chown -R appuser /app

USER root
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

EXPOSE 8000
