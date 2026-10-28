#!/usr/bin/env python3
"""Contrôler la réplication et les pannes du cluster."""

from collections import Counter
from pathlib import Path
import shlex
import subprocess
import sys
import time
import urllib.request
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lab.manage import ssh_args


def remote(name, command, check=True):
    result = subprocess.run(ssh_args(name) + [command], capture_output=True, text=True, timeout=60)
    print(f"$ {name}: {command}", flush=True)
    print(result.stdout + result.stderr, end="", flush=True)
    if check and result.returncode:
        raise RuntimeError(f"Commande échouée sur {name}.")
    return result


def sql(name, query, check=True):
    options = "--batch" if query.startswith("SHOW") else "--batch --skip-column-names"
    return remote(name, "sudo mariadb " + options + " -e " + shlex.quote(query), check)


def requests(count=8):
    responses = []
    for _ in range(count):
        with urllib.request.urlopen("http://127.0.0.1:8080/", timeout=8) as response:
            body = response.read().decode()
            backend = response.headers.get("X-Backend")
            assert response.status == 200
            assert "Clavier" in body
            responses.append((backend, body))
    print("Répartition :", dict(Counter(item[0] for item in responses)), flush=True)
    return responses


def main():
    print(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), flush=True)
    token = uuid.uuid4().hex
    sql("db1", "CREATE TABLE IF NOT EXISTS shop.replication_checks (token VARCHAR(32) PRIMARY KEY); INSERT INTO shop.replication_checks VALUES ('" + token + "');")
    for attempt in range(20):
        result = sql("db2", "SELECT token FROM shop.replication_checks WHERE token='" + token + "'", check=False)
        if token in result.stdout:
            break
        time.sleep(1)
    else:
        raise RuntimeError("La donnée de contrôle n'a pas été répliquée.")
    sql("db2", "SHOW SLAVE STATUS\\G")
    assert {item[0] for item in requests(12)} == {"web1", "web2"}
    print("PASS : les deux serveurs web répondent et les données sont répliquées.", flush=True)

    try:
        remote("web1", "sudo systemctl stop nginx")
        time.sleep(4)
        assert {item[0] for item in requests()} == {"web2"}
        print("PASS : le service reste disponible avec web1 arrêté.", flush=True)
    finally:
        remote("web1", "sudo systemctl start nginx")
    time.sleep(3)

    try:
        remote("db1", "sudo systemctl stop mariadb")
        time.sleep(4)
        responses = requests()
        assert all("<strong>db2</strong>" in item[1] for item in responses)
        assert sql("db2", "SELECT @@read_only").stdout.strip() == "1"
        print("PASS : lecture maintenue sur db2 pendant la panne de db1 ; la réplique reste en lecture seule.", flush=True)
    finally:
        remote("db1", "sudo systemctl start mariadb")

    for attempt in range(30):
        result = sql("db2", "SHOW SLAVE STATUS\\G")
        if "Slave_IO_Running: Yes" in result.stdout and "Slave_SQL_Running: Yes" in result.stdout:
            break
        time.sleep(2)
    else:
        raise RuntimeError("La réplication ne reprend pas après le retour du primaire.")
    time.sleep(3)
    assert {item[0] for item in requests(12)} == {"web1", "web2"}
    print("PASS : les services et la réplication sont rétablis après les pannes.", flush=True)


if __name__ == "__main__":
    main()
