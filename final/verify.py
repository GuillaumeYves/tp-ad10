#!/usr/bin/env python3
"""Vérifier l'infrastructure intégrée dans son état final."""

from collections import Counter
import json
from pathlib import Path
import shlex
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lab.manage import ROOT, ssh_args, wait
from tp5.capture_dashboard import capture

EVIDENCE = ROOT / 'final/evidence'
CONTEXT = ssl.create_default_context(cafile=str(ROOT / '.lab/tls/edge.crt'))
HOSTS = ['edge', 'web1', 'web2', 'db1', 'db2', 'monitor']


def remote(name, command, user='alice', content=None, check=True):
    result = subprocess.run(ssh_args(name, user) + [command], input=content, capture_output=True, text=True, timeout=90)
    print(f'$ {user}@{name}: {command}\n{result.stdout}{result.stderr}', flush=True)
    if check and result.returncode:
        raise RuntimeError(f'Commande échouée sur {name}.')
    return result


def request(count=8, database=None):
    backends = []
    for _ in range(count):
        with urllib.request.urlopen('https://127.0.0.1:8443/', context=CONTEXT, timeout=8) as response:
            content = response.read().decode()
            assert response.status == 200 and 'Clavier' in content
            if database:
                assert f'<strong>{database}</strong>' in content
            backends.append(response.headers['X-Backend'])
    print('Réponses HTTPS :', dict(Counter(backends)), flush=True)
    return set(backends)


def query(expression):
    url = 'http://127.0.0.1:9090/api/v1/query?' + urllib.parse.urlencode({'query': expression})
    with urllib.request.urlopen(url, timeout=10) as response:
        return json.load(response)['data']['result']


def probe(source, target, expected):
    program = "import socket\nresults={}\n"
    program += f"for port in {list(expected)}:\n s=socket.socket(); s.settimeout(2); results[port]=s.connect_ex(({target!r},port))==0; s.close()\n"
    program += f"print(results)\nassert results == {expected!r}\n"
    remote(source, 'python3 -c ' + shlex.quote(program), user='labadmin' if source == 'tp1-admin' else 'alice')


def main():
    print(time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), flush=True)
    assert request(12) == {'web1', 'web2'}
    print('PASS : HTTPS vérifié avec le certificat local et répartition sur les deux serveurs.', flush=True)

    for name in HOSTS:
        remote(name, 'sudo sshd -T | grep -E "^(allowusers|permitrootlogin|passwordauthentication|authenticationmethods) "; systemctl is-active nftables fail2ban auditd; sudo auditctl -l')
        for account in ['root', 'labadmin']:
            assert remote(name, 'true', account, check=False).returncode != 0
        result = remote(name, 'sudo nft list ruleset')
        assert 'policy drop' in result.stdout
        (EVIDENCE / f'{name}-nftables.txt').write_text(result.stdout)
    print('PASS : Alice seule autorisée en SSH, pare-feu et services de sécurité actifs sur six VM.', flush=True)

    probe('tp1-admin', '192.168.77.21', {22: True, 80: False, 9100: False})
    probe('tp1-admin', '192.168.77.31', {22: True, 3306: False})
    probe('edge', '192.168.77.21', {80: True})
    probe('web1', '192.168.77.20', {3306: True, 3307: True})
    probe('monitor', '192.168.77.21', {9100: True})
    print('PASS : les flux autorisés passent ; les autres sources sont filtrées.', flush=True)

    remote('db1', 'sudo bash -s', content=(ROOT / 'final/check-backup.sh').read_text())

    try:
        remote('web1', 'sudo systemctl stop nginx')
        time.sleep(4)
        assert request() == {'web2'}
        print('PASS : service HTTPS disponible pendant l’arrêt de web1.', flush=True)
    finally:
        remote('web1', 'sudo systemctl start nginx')
    time.sleep(3)

    try:
        remote('db1', 'sudo systemctl stop mariadb')
        time.sleep(4)
        request(database='db2')
        print('PASS : lectures HTTPS maintenues sur db2 pendant la panne du primaire.', flush=True)
    finally:
        remote('db1', 'sudo systemctl start mariadb')

    remote('web1', 'sudo reboot', check=False)
    time.sleep(5)
    wait('web1', 'alice')
    remote('web1', 'systemctl is-active nginx php8.3-fpm nftables fail2ban auditd prometheus-node-exporter ad10-service-metrics.timer; systemctl is-active systemd-networkd-wait-online')
    time.sleep(4)
    assert request(12) == {'web1', 'web2'}
    print('PASS : services, accès SSH et pare-feu persistants après redémarrage de web1.', flush=True)

    for attempt in range(50):
        nodes = query('up{job="nodes"}')
        replica = query('ad10_replica_io_running{host="db2"}')
        if len(nodes) == 6 and all(item['value'][1] == '1' for item in nodes) and replica and replica[0]['value'][1] == '1':
            break
        time.sleep(3)
    else:
        raise RuntimeError('La supervision ou la réplication ne sont pas revenues à la normale.')
    services = query('ad10_service_up')
    assert len(services) == 12 and all(item['value'][1] == '1' for item in services)
    assert query('ad10_database_up{host="db1"}')[0]['value'][1] == '1'
    assert query('ad10_database_up{host="db2"}')[0]['value'][1] == '1'
    assert query('ad10_replica_sql_running{host="db2"}')[0]['value'][1] == '1'
    assert query('ad10_backup_last_success_timestamp_seconds{host="db1"}')
    (EVIDENCE / 'monitoring-state.json').write_text(json.dumps({'nodes': nodes, 'services': services, 'replication': replica}, indent=2) + '\n')
    for attempt in range(10):
        if not query('ALERTS{alertstate="firing"}'):
            break
        time.sleep(5)
    else:
        raise RuntimeError('Des alertes restent actives après le rétablissement.')
    capture(EVIDENCE / 'grafana-cluster.png')
    print('PASS : six VM et leurs services supervisés, réplication rétablie et sauvegarde visible.', flush=True)


if __name__ == '__main__':
    main()
