FROM python:3.13-slim
WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive

ARG TZ=UTC

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      git tzdata \
 && ln -sf /usr/share/zoneinfo/${TZ} /etc/localtime \
 && echo ${TZ} > /etc/timezone \
 && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ARG USER_ID=500
RUN groupadd -g ${USER_ID} appgroup && \
    useradd -u ${USER_ID} -g appgroup -m appuser && \
    chown -R appuser:appgroup /app /entrypoint.sh

USER appuser

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
