#!/bin/bash
set -e
# Copy DNS resolver config to postfix chroot
cp -f /etc/resolv.conf /var/spool/postfix/etc/resolv.conf
cp -f /etc/services /var/spool/postfix/etc/services 2>/dev/null || true
# Start postfix in foreground
exec postfix start-fg
