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
docker-compose up -d db
sleep 1

echo "==> Kill all db connections"
docker-compose exec db psql -U postgres -c 'SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE pid != pg_backend_pid()'

echo "==> Drop and recreate database"
docker-compose exec db psql -U postgres -c "DROP DATABASE IF EXISTS ${LOCAL_DATABASE}"
docker-compose exec db psql -U postgres -c "CREATE DATABASE ${LOCAL_DATABASE}"

echo "==> Restore data"
docker-compose exec -T db psql -U postgres "${LOCAL_DATABASE}" < "$DATA_FILE"

echo "==> Create superuser"
cat<<EOF | docker-compose run -T --no-deps --rm app poetry run python manage.py shell
from mesads.users.models import User

User.objects.create_superuser('${SUPERUSER_USERNAME}', '${SUPERUSER_PASSWORD}')
EOF

echo "==> Give ADSManagerAdministrator permissions to the new user"
for id in ${DEFAULT_ADS_MANAGER_ADMINISTRATOR}; do
    echo "==> ... For ADSManagerAdministrator ${id}"
    cat<<EOF | docker-compose run -T --no-deps --rm app poetry run python manage.py shell

from mesads.app.models import ADSManagerAdministrator
from mesads.users.models import User

user = User.objects.get(email='${SUPERUSER_USERNAME}')
ads_manager_administrator = ADSManagerAdministrator.objects.get(id=${id})

ads_manager_administrator.users.add(user)
ads_manager_administrator.save()
EOF
done

echo "==> Give ADSManager permissions to the new user"
for id in ${DEFAULT_ADS_MANAGER}; do
    echo "==> ... For ADSManager ${id}"
    cat<<EOF | docker-compose run -T --no-deps --rm app poetry run python manage.py shell

from mesads.app.models import ADSManager, ADSManagerRequest
from mesads.users.models import User

user = User.objects.get(email='${SUPERUSER_USERNAME}')
ads_manager = ADSManager.objects.get(id=${id})
ads_manager_request = ADSManagerRequest(user=user, ads_manager=ads_manager, accepted=True)
ads_manager_request.save()
EOF
done
