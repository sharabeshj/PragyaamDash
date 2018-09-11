FROM postgres:9.4

ENTRYPOINT []
CMD export POSTGRES_DB=pragyaam_test; export POSTGRES_USER=sharbesh; export POSTGRES_PASSWORD=$(cat /etc/secrets/djangouserpw)  ;./docker-entrypoint.sh postgres;