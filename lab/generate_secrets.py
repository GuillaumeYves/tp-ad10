#!/usr/bin/env python3
"""Créer les identifiants locaux sans les afficher."""

import json
import os
from pathlib import Path
import secrets

folder = Path(__file__).resolve().parents[1] / ".lab"
folder.mkdir(mode=0o700, exist_ok=True)
destination = folder / "secrets.json"
if not destination.exists():
    descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        json.dump({name: secrets.token_urlsafe(32) for name in ["db_password", "replication_password", "grafana_password"]}, stream, indent=2)
        stream.write("\n")
    print("Secrets créés dans .lab/secrets.json.")
else:
    print("Les secrets existants sont conservés.")
