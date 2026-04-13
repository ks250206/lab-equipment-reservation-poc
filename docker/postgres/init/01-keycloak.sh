#!/usr/bin/env bash
set -euo pipefail

kc_db_name="${KC_DB_NAME:-keycloak}"
kc_db_user="${KC_DB_USERNAME:-keycloak}"
kc_db_password="${KC_DB_PASSWORD:-keycloak_dev_password}"

psql \
  -v ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  --set=kc_db_name="$kc_db_name" \
  --set=kc_db_user="$kc_db_user" \
  --set=kc_db_password="$kc_db_password" <<'SQL'
SELECT format('CREATE USER %I WITH PASSWORD %L', :'kc_db_user', :'kc_db_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'kc_db_user')\gexec

SELECT format('ALTER USER %I WITH PASSWORD %L', :'kc_db_user', :'kc_db_password')
WHERE EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'kc_db_user')\gexec

SELECT format('CREATE DATABASE %I OWNER %I', :'kc_db_name', :'kc_db_user')
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'kc_db_name')\gexec
SQL
