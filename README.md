# Administration avancée de serveurs Linux

Travaux pratiques réalisés sur des VM Ubuntu Server 24.04 LTS dédiées.

| Exercice | Sujet | Dossier |
| --- | --- | --- |
| TP1 | ACL, sauvegarde et gestion de charge | [tp1](tp1/) |
| TP2 | SSH, pare-feu et audit | tp2 |
| TP3 | Services web, réplication et répartition de charge | tp3 |
| TP4 | Bash et Ansible | tp4 |
| TP5 | Supervision et alertes | tp5 |
| Projet final | Infrastructure intégrée | final |

Chaque exercice terminé fait l'objet d'un commit distinct. Les rapports contiennent les commandes exécutées, les configurations et les résultats des vérifications.

## Laboratoire

Les machines utilisent QEMU/KVM. WSL héberge l'hyperviseur ; chaque serveur possède son propre noyau Linux, son disque et systemd. Les services du TP sont installés dans les VM.

```bash
sudo apt-get install qemu-system-x86 qemu-utils cloud-image-utils python3-venv
sudo usermod -aG kvm "$USER"
# Ouvrir une nouvelle session après l'ajout au groupe.
python3 lab/manage.py start tp1-admin
python3 lab/manage.py ssh tp1-admin
```

Pour l'automatisation et les captures :

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install firefox
sudo .venv/bin/playwright install-deps firefox
```

Les disques, clés privées et journaux de démarrage restent dans `.lab/`, exclu de Git. Les redirections de ports écoutent uniquement sur `127.0.0.1`. Le réseau privé des VM utilise `192.168.77.0/24` sur une seconde carte virtuelle.

L'image officielle est téléchargée avec vérification SHA-256. Sources : [images Ubuntu Minimal](https://cloud-images.ubuntu.com/minimal/releases/noble/release/), [documentation QEMU](https://www.qemu.org/docs/master/system/invocation.html).
