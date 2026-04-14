#!/bin/bash

set -e

PROD_ENV_FILE=$(dirname $0)/../.prod.env
LOCAL_ENV_FILE=$(dirname $0)/../.local.env

. "${PROD_ENV_FILE}"
. "${LOCAL_ENV_FILE}"

echo "==> Retrieve data from production database"
if [[ -f "$DATA_FILE" ]]; then
  read -r -p "File $DATA_FILE already exists. Force redownload? [Y/n]" REUSE
fi

if [[ "${REUSE:-y}" =~ ^[yY]$ ]]; then
    docker run --rm -ti postgres pg_dump -x "postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}" > "$DATA_FILE"
fi

echo "==> Start db container"
docker compose up -d db
sleep 1

echo "==> Kill all db connections"
docker compose exec db psql -U postgres -c 'SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE pid != pg_backend_pid()'

echo "==> Drop and recreate database"
docker compose exec db psql -U postgres -c "DROP DATABASE IF EXISTS ${LOCAL_DATABASE}"
docker compose exec db psql -U postgres -c "CREATE DATABASE ${LOCAL_DATABASE}"

echo "==> Restore data"
docker compose exec -T db psql -U postgres "${LOCAL_DATABASE}" < "$DATA_FILE"


