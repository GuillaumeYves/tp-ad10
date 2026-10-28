#!/usr/bin/env python3
"""Vérifier la collecte, le tableau de bord et une alerte réelle."""

import base64
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lab.manage import ROOT, ssh_args
from tp5.capture_dashboard import capture

EVIDENCE = ROOT / 'tp5/evidence'


def remote(name, command, content=None, check=True):
    result = subprocess.run(ssh_args(name) + [command], input=content, text=True, capture_output=True, timeout=90)
    print(f'$ {name}: {command}\n{result.stdout}{result.stderr}', flush=True)
    if check and result.returncode:
        raise RuntimeError(f'Commande échouée sur {name}.')
    return result


def api(path, port=9090, authenticated=False):
    request = urllib.request.Request(f'http://127.0.0.1:{port}{path}')
    if authenticated:
        password = json.loads((ROOT / '.lab/secrets.json').read_text())['grafana_password']
        authorization = base64.b64encode(('admin:' + password).encode()).decode()
        request.add_header('Authorization', 'Basic ' + authorization)
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.load(response)


def main():
    EVIDENCE.mkdir(exist_ok=True)
    for attempt in range(40):
        try:
            targets = api('/api/v1/targets')['data']['activeTargets']
            nodes = [item for item in targets if item['labels']['job'] == 'nodes']
            if len(nodes) == 2 and all(item['health'] == 'up' for item in nodes):
                break
        except (OSError, ValueError):
            pass
        time.sleep(3)
    else:
        raise RuntimeError('Les deux exporters ne sont pas disponibles.')
    (EVIDENCE / 'targets.json').write_text(json.dumps(targets, indent=2) + '\n')
    print('PASS : les deux serveurs sont collectés par Prometheus.', flush=True)

    remote('monitor', 'sudo tee /tmp/ad10-alert-tests.yml >/dev/null', (ROOT / 'tp5/alert-tests.yml').read_text())
    remote('monitor', 'promtool check config /etc/prometheus/prometheus.yml; promtool test rules /tmp/ad10-alert-tests.yml')
    dashboard = api('/api/dashboards/uid/ad10-cluster', 3000, True)['dashboard']
    assert len(dashboard['panels']) == 7
    print('PASS : le tableau de bord personnalisé est provisionné.', flush=True)

    remote('web1', 'sudo tee /tmp/ad10-memory-load.py >/dev/null', (ROOT / 'tp5/memory-load.py').read_text())
    try:
        remote('web1', 'sudo systemd-run --unit=ad10-memory-test --collect -p MemoryMax=600M -p RuntimeMaxSec=250 /usr/bin/python3 /tmp/ad10-memory-load.py')
        deadline = time.monotonic() + 210
        while time.monotonic() < deadline:
            alerts = api('/api/v1/alerts')['data']['alerts']
            matching = [item for item in alerts if item['labels'].get('alertname') == 'MemoryUsageHigh' and item['labels'].get('host') == 'web1']
            print('État de l’alerte mémoire :', [item['state'] for item in matching], flush=True)
            if any(item['state'] == 'firing' for item in matching):
                (EVIDENCE / 'alerts-firing.json').write_text(json.dumps(alerts, indent=2, ensure_ascii=False) + '\n')
                break
            time.sleep(15)
        else:
            raise RuntimeError('L’alerte mémoire ne s’est pas déclenchée.')
        time.sleep(10)
        received = api('/api/v2/alerts', 9093)
        assert any(item['labels'].get('alertname') == 'MemoryUsageHigh' for item in received)
        (EVIDENCE / 'alertmanager.json').write_text(json.dumps(received, indent=2, ensure_ascii=False) + '\n')
        capture(EVIDENCE / 'grafana-memory-alert.png')
        print('PASS : alerte réelle après dépassement prolongé, reçue par Alertmanager.', flush=True)
    finally:
        remote('web1', 'sudo systemctl stop ad10-memory-test', check=False)

    for attempt in range(20):
        alerts = api('/api/v1/alerts')['data']['alerts']
        if not any(item['labels'].get('alertname') == 'MemoryUsageHigh' for item in alerts):
            break
        time.sleep(5)
    else:
        raise RuntimeError('L’alerte mémoire ne s’est pas résolue.')
    time.sleep(20)
    journal = remote('monitor', 'sudo journalctl -u ad10-alert-receiver --since "10 minutes ago" --no-pager -o cat').stdout
    (EVIDENCE / 'notification-journal.txt').write_text(journal)
    assert 'MemoryUsageHigh' in journal and '"status": "firing"' in journal and '"status": "resolved"' in journal
    capture(EVIDENCE / 'grafana-dashboard.png')
    remote('monitor', 'dpkg-query -W prometheus prometheus-node-exporter prometheus-alertmanager grafana')
    print('PASS : notification locale de déclenchement et de résolution ; mémoire libérée.', flush=True)


if __name__ == '__main__':
    main()
