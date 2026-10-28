#!/usr/bin/env python3
"""Vérifications réseau et sécurité du TP2."""

from pathlib import Path
import shlex
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lab.manage import ROOT, ssh_args


def remote(name, command, user="labadmin", check=True, input_text=None):
    result = subprocess.run(ssh_args(name, user) + [command], input=input_text, capture_output=True, text=True, timeout=90)
    print(f"$ {user}@{name}: {command}", flush=True)
    print(result.stdout + result.stderr, end="", flush=True)
    if check and result.returncode:
        raise RuntimeError(f"Commande échouée : {name}, code {result.returncode}.")
    return result


def main():
    remote("tp2-security", "sudo bash -s", "alice", input_text=(ROOT / "tp2/verify.sh").read_text())
    for user in ["root", "labadmin"]:
        result = remote("tp2-security", "true", user, check=False)
        assert result.returncode != 0, f"Connexion interdite acceptée : {user}."
    print("PASS : Alice se connecte par clé, root et labadmin sont refusés.", flush=True)

    try:
        for port in [80, 443, 8088]:
            remote("tp2-security", f"sudo systemd-run --unit=ad10-test-{port} --collect /usr/bin/python3 -m http.server {port}", "alice")
        time.sleep(2)
        probe = """import socket
results = {}
for port in [22, 80, 443, 8088]:
    connection = socket.socket()
    connection.settimeout(2)
    results[port] = connection.connect_ex(('192.168.77.12', port)) == 0
    connection.close()
print(results)
assert results == {22: True, 80: True, 443: True, 8088: False}
"""
        remote("tp1-admin", "python3 -c " + shlex.quote(probe))
        remote("tp2-security", "python3 -c " + shlex.quote("import socket; s=socket.create_connection(('127.0.0.1',8088),2); print('Le service 8088 écoute bien localement.'); s.close()"), "alice")
        print("PASS : ports 22, 80, 443 ouverts ; port 8088 filtré malgré un service actif.", flush=True)

        attempt = """import subprocess, time
for _ in range(4):
    result = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=accept-new', '-o', 'UserKnownHostsFile=/tmp/ad10-probe-hosts', '-o', 'ConnectTimeout=2', '-o', 'IdentitiesOnly=yes', '-o', 'IdentityFile=/dev/null', 'intruder@192.168.77.12', 'true'], capture_output=True, text=True)
    print('Tentative refusée :', result.returncode)
    time.sleep(1)
"""
        remote("tp1-admin", "python3 -c " + shlex.quote(attempt))
        time.sleep(3)
        result = remote("tp2-security", "sudo fail2ban-client status sshd", "alice")
        assert "192.168.77.11" in result.stdout, "L'adresse de test n'a pas été bannie."
        print("PASS : Fail2ban a banni la source après de vrais échecs SSH.", flush=True)
    finally:
        remote("tp2-security", "sudo fail2ban-client set sshd unbanip 192.168.77.11", "alice", check=False)
        for port in [80, 443, 8088]:
            remote("tp2-security", f"sudo systemctl stop ad10-test-{port}", "alice", check=False)
    remote("tp2-security", "sudo nft list ruleset", "alice")


if __name__ == "__main__":
    main()
