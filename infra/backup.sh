#!/usr/bin/env sh
# Online logical backup of the site database into the predictrx-backups volume.
# Backups contain identifiable clinical data: copy them only to encrypted, access-controlled storage.
#
#   infra/backup.sh                      # base compose file
#   COMPOSE_FILES="-f docker-compose.yml -f docker-compose.site.yml" infra/backup.sh
set -eu

COMPOSE_FILES=${COMPOSE_FILES:-"-f docker-compose.yml"}
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
TARGET="/app/backups/predictrx-${STAMP}.json.gz"

# shellcheck disable=SC2086
docker compose $COMPOSE_FILES exec -T api python -m app.ops_cli backup --out "$TARGET"
# shellcheck disable=SC2086
docker compose $COMPOSE_FILES exec -T api python -m app.ops_cli verify-audit
echo "Backup written to volume predictrx-backups: $TARGET"
