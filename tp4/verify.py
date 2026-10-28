#!/usr/bin/env python3
"""Contrôler les deux déploiements et leur idempotence."""

from pathlib import Path
import re
import subprocess
import sys
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lab.manage import ROOT, ssh_args

for name, port in [("tp4-web1", 8041), ("tp4-web2", 8042)]:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5) as response:
        assert response.status == 200
        assert response.headers["X-Backend"] == name
        assert "Nginx est opérationnel" in response.read().decode()
    result = subprocess.run(ssh_args(name) + ["sudo nft list ruleset; systemctl is-active nginx nftables; systemctl is-enabled nginx nftables"], capture_output=True, text=True, check=True)
    print(f"=== {name} ===\n{result.stdout}")
    log = (ROOT / "tp4/evidence/ansible-second-run.txt").read_text()
    assert re.search(re.escape(name) + r"\s+:.*changed=0\s+unreachable=0\s+failed=0", log)
    print(f"PASS : {name} répond, les services sont persistants et la seconde exécution ne change rien.")
