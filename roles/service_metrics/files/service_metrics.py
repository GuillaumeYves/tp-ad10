#!/usr/bin/env python3
"""Exposer l'état des services et de MariaDB via Node Exporter."""

import argparse
import os
from pathlib import Path
import subprocess
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--service', action='append', default=[])
parser.add_argument('--database', action='store_true')
parser.add_argument('--replica', action='store_true')
parser.add_argument('--backup', action='store_true')
args = parser.parse_args()
lines = [f'ad10_collection_timestamp_seconds {time.time():.0f}']
for service in args.service:
    result = subprocess.run(['systemctl', 'is-active', '--quiet', service], timeout=10)
    lines.append(f'ad10_service_up{{service="{service}"}} {int(result.returncode == 0)}')

if args.database:
    result = subprocess.run(['mariadb', '--batch', '--skip-column-names', '-e', 'SELECT @@read_only'], capture_output=True, text=True, timeout=10)
    lines.append(f'ad10_database_up {int(result.returncode == 0)}')
    lines.append(f'ad10_replica_expected {int(args.replica)}')
    if result.returncode == 0:
        lines.append(f'ad10_database_read_only {int(result.stdout.strip())}')
        if args.replica:
            status = subprocess.run(['mariadb', '-e', 'SHOW SLAVE STATUS\\G'], capture_output=True, text=True, timeout=10)
            fields = {line.split(':', 1)[0].strip(): line.split(':', 1)[1].strip()
                      for line in status.stdout.splitlines() if ':' in line}
            lines.append(f'ad10_replica_io_running {int(fields.get("Slave_IO_Running") == "Yes")}')
            lines.append(f'ad10_replica_sql_running {int(fields.get("Slave_SQL_Running") == "Yes")}')
            delay = fields.get('Seconds_Behind_Master', 'NULL')
            lines.append(f'ad10_replica_lag_seconds {int(delay) if delay.isdigit() else -1}')
if args.backup:
    marker = Path('/backup/last-success')
    lines.append(f'ad10_backup_last_success_timestamp_seconds {marker.read_text().strip() if marker.exists() else 0}')

destination = Path('/var/lib/prometheus/node-exporter/ad10_services.prom')
temporary = destination.with_suffix('.partial')
temporary.write_text('\n'.join(lines) + '\n')
os.chmod(temporary, 0o644)
temporary.replace(destination)
