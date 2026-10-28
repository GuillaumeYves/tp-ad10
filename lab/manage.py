#!/usr/bin/env python3
"""Gestion des VM du laboratoire."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / ".lab"
MACHINES = json.loads((ROOT / "lab/machines.json").read_text())
IMAGE_URL = "https://cloud-images.ubuntu.com/minimal/releases/noble/release/"
IMAGE_NAME = "ubuntu-24.04-minimal-cloudimg-amd64.img"


def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def prepare():
    STATE.mkdir(mode=0o700, exist_ok=True)
    key = STATE / "id_ed25519"
    if not key.exists():
        run("ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "ad10-lab", "-f", str(key))
    image = STATE / IMAGE_NAME
    if not image.exists():
        sums = urllib.request.urlopen(IMAGE_URL + "SHA256SUMS", timeout=60).read().decode()
        expected = next(line.split()[0] for line in sums.splitlines() if line.split()[-1].lstrip("*") == IMAGE_NAME)
        temporary = image.with_suffix(".download")
        print("Téléchargement de l'image Ubuntu officielle.", flush=True)
        urllib.request.urlretrieve(IMAGE_URL + IMAGE_NAME, temporary)
        actual = hashlib.file_digest(temporary.open("rb"), "sha256").hexdigest()
        if actual != expected:
            temporary.unlink()
            raise RuntimeError("La somme SHA-256 de l'image est incorrecte.")
        temporary.replace(image)
        (STATE / "image.json").write_text(json.dumps({"url": IMAGE_URL + IMAGE_NAME, "sha256": actual}, indent=2) + "\n")
    return image, key


def ssh_args(name, user="labadmin"):
    machine = MACHINES[name]
    return ["ssh", "-i", str(STATE / "id_ed25519"), "-p", str(machine["ssh_port"]),
            "-o", "StrictHostKeyChecking=accept-new", "-o", f"UserKnownHostsFile={STATE / 'known_hosts'}",
            "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", f"{user}@127.0.0.1"]


def pid_for(name):
    pidfile = STATE / name / "qemu.pid"
    if not pidfile.exists():
        return None
    pid = int(pidfile.read_text().strip())
    try:
        command = Path(f"/proc/{pid}/cmdline").read_bytes()
        if b"qemu-system" in command and str(STATE / name / "disk.qcow2").encode() in command:
            return pid
    except FileNotFoundError:
        pass
    return None


def start(name):
    if pid_for(name):
        print(f"{name} fonctionne déjà.")
        return
    image, key = prepare()
    machine = MACHINES[name]
    folder = STATE / name
    folder.mkdir(exist_ok=True)
    disk = folder / "disk.qcow2"
    if not disk.exists():
        run("qemu-img", "create", "-f", "qcow2", "-F", "qcow2", "-b", str(image), str(disk), "12G")
    public_key = key.with_suffix(".pub").read_text().strip()
    user_data = folder / "user-data"
    user_data.write_text(f"""#cloud-config
hostname: {name}
manage_etc_hosts: true
users:
  - name: labadmin
    shell: /bin/bash
    groups: [sudo]
    sudo: ALL=(ALL) NOPASSWD:ALL
    lock_passwd: true
    ssh_authorized_keys:
      - {public_key}
ssh_pwauth: false
disable_root: true
""")
    (folder / "meta-data").write_text(f"instance-id: ad10-{name}\nlocal-hostname: {name}\n")
    suffix = int(machine["address"].split(".")[-1])
    network = folder / "network-config"
    network.write_text(f"""version: 2
ethernets:
  wan:
    match:
      macaddress: '52:54:00:10:00:{suffix:02x}'
    dhcp4: true
    dhcp6: false
    accept-ra: false
  lan:
    match:
      macaddress: '52:54:00:77:00:{suffix:02x}'
    addresses: [{machine['address']}/24]
    dhcp4: false
    dhcp6: false
    accept-ra: false
    optional: true
""")
    seed = folder / "seed.img"
    if not seed.exists():
        run("cloud-localds", "--network-config", str(network), str(seed), str(user_data), str(folder / "meta-data"))
    forwards = f",hostfwd=tcp:127.0.0.1:{machine['ssh_port']}-:22"
    for host, guest in machine.get("ports", {}).items():
        forwards += f",hostfwd=tcp:127.0.0.1:{host}-:{guest}"
    run("qemu-system-x86_64", "-name", f"ad10-{name}", "-enable-kvm", "-cpu", "host",
        "-m", str(machine["memory"]), "-smp", "2", "-display", "none", "-daemonize",
        "-pidfile", str(folder / "qemu.pid"), "-serial", f"file:{folder / 'console.log'}",
        "-monitor", f"unix:{folder / 'monitor.sock'},server,nowait",
        "-drive", f"file={disk},format=qcow2,if=virtio",
        "-drive", f"file={seed},format=raw,if=virtio,readonly=on",
        "-netdev", "user,id=wan" + forwards,
        "-device", f"virtio-net-pci,netdev=wan,mac=52:54:00:10:00:{suffix:02x}",
        "-netdev", "socket,id=lan,mcast=239.77.0.1:17777,localaddr=127.0.0.1",
        "-device", f"virtio-net-pci,netdev=lan,mac=52:54:00:77:00:{suffix:02x}")
    print(f"{name} démarrée, SSH sur 127.0.0.1:{machine['ssh_port']}.", flush=True)


def wait(name, user):
    deadline = time.monotonic() + 240
    while time.monotonic() < deadline:
        result = subprocess.run(ssh_args(name, user) + ["true"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode == 0:
            run(*(ssh_args(name, user) + ["sudo cloud-init status --wait"]))
            return
        time.sleep(3)
    raise RuntimeError(f"SSH indisponible sur {name}. Consulter .lab/{name}/console.log.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["start", "wait", "ssh", "stop", "status"])
    parser.add_argument("name", choices=[*MACHINES, "all"])
    parser.add_argument("--user", default="labadmin")
    args, command = parser.parse_known_args()
    names = list(MACHINES) if args.name == "all" else [args.name]
    for name in names:
        if args.action == "start":
            start(name)
        elif args.action == "wait":
            wait(name, args.user)
        elif args.action == "ssh":
            sys.exit(subprocess.call(ssh_args(name, args.user) + command))
        elif args.action == "status":
            print(f"{name}: {'en marche' if pid_for(name) else 'arrêtée'}")
        elif args.action == "stop" and pid_for(name):
            # Arrêter le système invité avant de libérer son disque.
            subprocess.run(ssh_args(name, args.user) + ["sudo poweroff"], check=False)
            deadline = time.monotonic() + 60
            while pid_for(name) and time.monotonic() < deadline:
                time.sleep(1)
            if pid_for(name):
                raise RuntimeError(f"{name} ne s'est pas arrêtée. Consulter sa console.")
            print(f"{name} arrêtée.")


if __name__ == "__main__":
    main()
