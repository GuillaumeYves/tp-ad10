#!/usr/bin/env bash
set -euo pipefail
umask 077

install -d -m 0700 /backup
exec 9>/run/lock/backup-shop.lock
flock -n 9 || exit 0
archive="/backup/shop-$(date -u +%Y%m%dT%H%M%S%NZ).sql.gz"
temporary="${archive}.partial"
trap 'rm -f -- "$temporary"' EXIT
mariadb-dump --single-transaction --routines --events --triggers shop | gzip > "$temporary"
gzip -t "$temporary"
mv -- "$temporary" "$archive"
date +%s > /backup/last-success
printf 'Sauvegarde créée : %s\n' "$archive"
