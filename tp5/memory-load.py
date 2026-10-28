#!/usr/bin/env python3
"""Maintenir une charge mémoire contrôlée pendant le test d'alerte."""

import time

memory = {}
with open('/proc/meminfo') as stream:
    for line in stream:
        name, value, *_ = line.split()
        memory[name.rstrip(':')] = int(value) * 1024

target = int(memory['MemAvailable'] - 0.13 * memory['MemTotal'])
if target <= 0:
    raise RuntimeError('La mémoire est déjà trop occupée pour ce test.')
allocation = bytearray(target)
# Toucher chaque page pour rendre l'allocation effective.
for offset in range(0, len(allocation), 4096):
    allocation[offset] = 1
print(f'Allocation de test : {target // 1048576} Mio.', flush=True)
time.sleep(240)
