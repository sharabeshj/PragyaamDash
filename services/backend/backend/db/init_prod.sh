#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "postgres" --dbname "pragyaam_prod" <<-EOSQL

EOSQL