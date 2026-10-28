#!/usr/bin/env bash
set -euo pipefail
umask 077

if [[ $EUID -ne 0 ]]; then
    echo "La sauvegarde nécessite les droits root." >&2
    exit 1
fi

install -d -m 0700 /backup
exec 9>/run/lock/backup-data.lock
flock -n 9 || exit 0

archive="/backup/data-$(date -u +%Y%m%dT%H%M%S%NZ).tar.gz"
temporary="${archive}.partial"
trap 'rm -f -- "$temporary"' EXIT

# Préserver les propriétaires, les attributs et les ACL.
tar --acls --xattrs --numeric-owner -czpf "$temporary" -C /srv data
tar -tzf "$temporary" >/dev/null
mv -- "$temporary" "$archive"
printf 'Sauvegarde créée : %s\n' "$archive"
