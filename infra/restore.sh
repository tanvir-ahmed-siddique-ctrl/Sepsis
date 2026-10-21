#!/usr/bin/env sh
# Restore a logical backup. The API must be stopped: restore refuses while a writer holds the lease.
#
#   infra/restore.sh predictrx-20261016T020000Z.json.gz          # into an empty database
#   FORCE=1 infra/restore.sh predictrx-20261016T020000Z.json.gz  # replace existing contents
set -eu

if [ $# -ne 1 ]; then
  echo "usage: $0 <backup file name inside the predictrx-backups volume>" >&2
  exit 64
fi

COMPOSE_FILES=${COMPOSE_FILES:-"-f docker-compose.yml"}
FORCE_FLAG=""
if [ "${FORCE:-0}" = "1" ]; then
  FORCE_FLAG="--force"
fi

# shellcheck disable=SC2086
docker compose $COMPOSE_FILES stop api web
# shellcheck disable=SC2086
docker compose $COMPOSE_FILES run --rm --no-deps api \
  python -m app.ops_cli restore --input "/app/backups/$1" $FORCE_FLAG
# shellcheck disable=SC2086
docker compose $COMPOSE_FILES run --rm --no-deps api python -m app.ops_cli verify-audit
# shellcheck disable=SC2086
docker compose $COMPOSE_FILES up -d api web
