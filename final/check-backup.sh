#!/usr/bin/env bash
set -euo pipefail

/usr/local/sbin/backup-shop
archive=$(find /backup -maxdepth 1 -name 'shop-*.sql.gz' | sort | tail -n 1)
test -n "$archive"
database=ad10_restore_check
if [[ $(mariadb -NBe "SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name='$database'") != 0 ]]; then
    echo "La base de contrôle existe déjà. Vérifier son origine avant de poursuivre." >&2
    exit 1
fi
trap 'mariadb -e "DROP DATABASE IF EXISTS ad10_restore_check"' EXIT
mariadb -e "CREATE DATABASE $database"
gzip -dc -- "$archive" | mariadb "$database"
original=$(mariadb -NBe 'CHECKSUM TABLE shop.products' | awk '{print $2}')
restored=$(mariadb -NBe 'CHECKSUM TABLE ad10_restore_check.products' | awk '{print $2}')
test "$original" = "$restored"
printf 'Archive : %s\n' "$archive"
printf 'Sommes de contrôle identiques : %s.\n' "$original"
mariadb -e 'SELECT COUNT(*) AS restored_products FROM ad10_restore_check.products'
printf 'PASS : sauvegarde et restauration dans une base distincte.\n'
