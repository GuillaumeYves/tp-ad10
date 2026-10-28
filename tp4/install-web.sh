#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "Exécuter ce script avec sudo." >&2
    exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y nginx
install -d -m 0755 /var/www/ad10-static
install -m 0644 "$(dirname "$0")/index.html" /var/www/ad10-static/index.html

cat > /etc/nginx/sites-available/ad10-static <<EOF
server {
    listen 80 default_server;
    server_name _;
    root /var/www/ad10-static;
    index index.html;
    server_tokens off;
    add_header X-Backend $(hostname) always;
}
EOF
ln -sfn /etc/nginx/sites-available/ad10-static /etc/nginx/sites-enabled/ad10-static
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable --now nginx
systemctl reload nginx
