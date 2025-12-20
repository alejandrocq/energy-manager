FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    postfix \
    ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Configure postfix to accept mail from backend
RUN postconf -e "myhostname=postfix" && \
    postconf -e "mydestination=localhost" && \
    postconf -e "mynetworks=127.0.0.0/8 172.16.0.0/12 192.168.0.0/16 10.0.0.0/8" && \
    postconf -e "inet_interfaces=all" && \
    postconf -e "inet_protocols=ipv4"

# Copy resolv.conf and services to chroot for DNS resolution
# Using a startup script to handle dynamic DNS
COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

EXPOSE 25

ENTRYPOINT ["/entrypoint.sh"]
