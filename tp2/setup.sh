#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "Exécuter ce script avec sudo." >&2
    exit 1
fi

source_dir=$(cd -- "$(dirname -- "$0")" && pwd)
key_file=${1:-/home/labadmin/.ssh/authorized_keys}
test -s "$key_file"
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y openssh-server fail2ban python3-systemd nftables auditd

if ! id alice >/dev/null 2>&1; then
    useradd --create-home --shell /bin/bash --groups sudo alice
fi
install -d -m 0700 -o alice -g alice /home/alice/.ssh
install -m 0600 -o alice -g alice "$key_file" /home/alice/.ssh/authorized_keys
printf 'alice ALL=(ALL) NOPASSWD: ALL\n' > /etc/sudoers.d/90-alice-ad10
chmod 0440 /etc/sudoers.d/90-alice-ad10
visudo -cf /etc/sudoers.d/90-alice-ad10

# Valider les fichiers avant de remplacer les configurations actives.
/usr/sbin/sshd -t -f "$source_dir/sshd_config"
nft -c -f "$source_dir/nftables.conf"
if [[ ! -f /etc/ssh/sshd_config.before-ad10 ]]; then
    cp -a /etc/ssh/sshd_config /etc/ssh/sshd_config.before-ad10
fi
install -m 0600 "$source_dir/sshd_config" /etc/ssh/sshd_config
install -m 0644 "$source_dir/nftables.conf" /etc/nftables.conf
install -m 0644 "$source_dir/sshd.local" /etc/fail2ban/jail.d/sshd.local
install -m 0640 "$source_dir/passwd.rules" /etc/audit/rules.d/passwd.rules

systemctl enable --now nftables auditd
nft -f /etc/nftables.conf
augenrules --load
systemctl enable fail2ban
systemctl restart fail2ban
systemctl reload ssh
printf 'Configuration terminée. Utiliser désormais le compte alice.\n'
