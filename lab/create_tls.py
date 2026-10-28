#!/usr/bin/env python3
"""Créer le certificat HTTPS local du laboratoire."""

import os
from pathlib import Path
import subprocess

folder = Path(__file__).resolve().parents[1] / '.lab/tls'
folder.mkdir(mode=0o700, parents=True, exist_ok=True)
certificate = folder / 'edge.crt'
key = folder / 'edge.key'
bundle = folder / 'edge.pem'
if not certificate.exists():
    subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:3072', '-nodes', '-days', '365',
                    '-subj', '/CN=ad10-lab', '-addext', 'subjectAltName=DNS:localhost,IP:127.0.0.1,IP:192.168.77.20',
                    '-keyout', str(key), '-out', str(certificate)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.chmod(key, 0o600)
if not bundle.exists():
    descriptor = os.open(bundle, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(certificate.read_bytes() + key.read_bytes())
print('Certificat et clé disponibles dans .lab/tls/.')
