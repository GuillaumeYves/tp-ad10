#!/usr/bin/env bash
set -euo pipefail

printf '=== Système et virtualisation ===\n'
date --iso-8601=seconds
hostnamectl
systemd-detect-virt

printf '\n=== Utilisateurs et ACL ===\n'
id alice
id bob
id carol
getfacl /srv/data
sudo -u alice sh -c 'printf "Données de test du TP1.\n" > /srv/data/check.txt'
sudo -u bob cat /srv/data/check.txt
if sudo -u bob touch /srv/data/bob.txt; then
    echo "ÉCHEC : Bob peut écrire." >&2
    exit 1
fi
if sudo -u carol ls /srv/data; then
    echo "ÉCHEC : Carol peut accéder aux données." >&2
    exit 1
fi
printf 'PASS : Alice écrit, Bob lit sans écrire, Carol ne peut pas accéder.\n'

printf '\n=== Sauvegarde et restauration ===\n'
/usr/local/sbin/backup-data
archive=$(find /backup -maxdepth 1 -name 'data-*.tar.gz' | sort | tail -n 1)
restore=$(mktemp -d)
trap 'rm -rf -- "$restore"' EXIT
tar --acls --xattrs --numeric-owner -xzpf "$archive" -C "$restore"
cmp /srv/data/check.txt "$restore/data/check.txt"
diff <(getfacl -cp /srv/data) <(getfacl -cp "$restore/data")
ls -lh "$archive"
cat /etc/cron.d/backup-data
systemctl is-active cron
printf 'PASS : contenu et ACL restaurés à l’identique.\n'

printf '\n=== Charge et priorité ===\n'
top -b -n 1 | head -n 12 || true
stress-ng --cpu 2 --timeout 15s &
stress_pid=$!
sleep 2
children=$(pgrep -P "$stress_pid" || true)
renice -n 10 -p "$stress_pid" $children
ps -o pid,ppid,ni,pcpu,comm -p "$stress_pid" ${children:+$(printf '%s\n' "$children" | sed 's/^/-p /')}
top -b -n 1 | head -n 16 || true
wait "$stress_pid"
printf 'PASS : processus et travailleurs exécutés avec nice=10.\n'
