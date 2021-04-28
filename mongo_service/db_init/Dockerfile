FROM mongo:4.2.12
COPY service_defs.json .
CMD mongoimport --jsonArray --host database --db metagenomic --collection services --file service_defs.json