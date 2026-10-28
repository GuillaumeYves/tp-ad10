#!/usr/bin/env python3
"""Créer les identifiants locaux sans les afficher."""

import json
import os
from pathlib import Path
import secrets

folder = Path(__file__).resolve().parents[1] / ".lab"
folder.mkdir(mode=0o700, exist_ok=True)
destination = folder / "secrets.json"
values = json.loads(destination.read_text()) if destination.exists() else {}
missing = [name for name in ["db_password", "replication_password", "grafana_password", "grafana_secret"] if name not in values]
if missing:
    values.update({name: secrets.token_urlsafe(32) for name in missing})
    temporary = destination.with_suffix('.partial')
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        json.dump(values, stream, indent=2)
        stream.write("\n")
    temporary.replace(destination)
    print("Secrets créés dans .lab/secrets.json.")
else:
    print("Les secrets existants sont conservés.")
