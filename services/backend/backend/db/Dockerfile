#base image
FROM postgres:10.4-alpine

#run create.sql on init
ADD create.sql /docker-entrypoint-initdb.d
# ADD init_dev.sh /docker-entrypoint-initdb.d
# ADD init_prod.sh /docker-entrypoint-initdb.d