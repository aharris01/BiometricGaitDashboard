#!/usr/bin/env bash
set -euo pipefail

# Read secrets provided in files
APP_DB="${APP_DB:-metadata_db}"
APP_USER="${APP_USER:-capstone_app}"
APP_PASSWORD="$(cat "${APP_PASSWORD_FILE}")"

# 1) Create db owned by bootstrap superuser
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<SQL
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = '${APP_DB}') THEN
        CREATE DATABASE "${APP_DB}";
    END IF;
END \$\$;
SQL

# 2) Create least-priviliged login role
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$APP_DB" <<SQL
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '${APP_USER}') THEN
        CREATE ROLE "${APP_USER}" LOGIN
            PASSWORD '${APP_PASSWORD}'
            NOSUPERUSER NOCREATEDB NOCREATEROLE INHERIT NOREPLICATION;
    END IF;
END \$\$;

-- 3) App schema isolated from "public"
CREATE SCHEMA IF NOT EXISTS app AUTHORIZATION "$POSTGRES_USER";

-- Lock down "public" schema
REVOKE CREATE ON SCHEMA public FROM PUBLIC;

-- 4) Grants for the app user on the app schema
GRANT CONNECT ON DATABASE "${APP_DB}" TO "${APP_USER}";
GRANT USAGE ON SCHEMA app TO "${APP_USER}";
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA app to "${APP_USER}";
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA app TO "${APP_USER}";

--5) Set default privileges for any new tables/sequences
ALTER DEFAULT PRIVILEGES IN SCHEMA app
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "${APP_USER}";
ALTER DEFAULT PRIVILEGES IN SCHEMA app
    GRANT USAGE, SELECT ON SEQUENCES TO "${APP_USER}";
SQL