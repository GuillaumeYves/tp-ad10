#!/usr/bin/env bash
set -euo pipefail

printf '=== Système ===\n'
date --iso-8601=seconds
hostnamectl
printf '\n=== Configuration SSH effective ===\n'
/usr/sbin/sshd -t
/usr/sbin/sshd -T | grep -E '^(permitrootlogin|allowusers|passwordauthentication|kbdinteractiveauthentication|authenticationmethods|pubkeyauthentication) '

printf '\n=== Pare-feu ===\n'
nft list ruleset
printf '\n=== Fail2ban ===\n'
fail2ban-client status sshd
printf '\n=== Audit ===\n'
auditctl -l
cat /etc/passwd >/dev/null
sleep 2
ausearch -if /var/log/audit/audit.log -k passwd_watch -x /usr/bin/cat -ts recent -i | tail -n 35
printf '\n=== Services ===\n'
systemctl is-active ssh nftables fail2ban auditd
