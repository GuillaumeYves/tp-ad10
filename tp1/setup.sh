#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "Exécuter ce script avec sudo." >&2
    exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y acl cron stress-ng procps

for account in alice bob carol; do
    if ! id "$account" >/dev/null 2>&1; then
        useradd --create-home --shell /bin/bash "$account"
    fi
done

install -d -m 0700 -o root -g root /srv/data /backup
setfacl -b /srv/data
setfacl -m u:alice:rwx,u:bob:r-x,u:carol:---,m::rwx /srv/data
# Transmettre les permissions aux nouveaux fichiers et sous-dossiers.
setfacl -d -m u::rwx,u:alice:rwx,u:bob:r-x,u:carol:---,g::---,m::rwx,o::--- /srv/data

install -m 0750 "$(dirname "$0")/backup.sh" /usr/local/sbin/backup-data
install -m 0644 "$(dirname "$0")/backup.cron" /etc/cron.d/backup-data
systemctl enable --now cron
getfacl /srv/data
