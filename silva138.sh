#!/bin/bash
# Utelises the docker wait command to run each container only after its parent has finished executing
# Future versions of this toll could implement this in some sort of dispatcher routine
ECHO OFF

cd qiime2
ENVFILE="--env-file .env.newsilva"
docker-compose ${ENVFILE} build
docker-compose ${ENVFILE} up database_init
docker-compose ${ENVFILE} up manifest_creator
docker wait manifest_creator
docker-compose ${ENVFILE} up metadata_creator
docker wait metadata_creator
docker-compose ${ENVFILE} up qiime_data_import
docker wait qiime_data_import
docker-compose ${ENVFILE} up qiime_qa
docker wait qiime_qa
docker-compose ${ENVFILE} up qiime_classifier
docker wait qiime_classifier
docker-compose ${ENVFILE} up qiime_phylogeny_tree
docker wait qiime_classifier
docker-compose ${ENVFILE} up qiime_frequency_tables
docker wait qiime_frequency_tables
docker wait qiime_phylogeny_tree
docker-compose ${ENVFILE} up qiime_diversity
docker wait qiime_diversity
docker-compose ${ENVFILE} up realtive_frequency_to_biom
docker wait realtive_frequency_to_biom
docker-compose ${ENVFILE} up lefse
docker wait lefse
docker-compose ${ENVFILE} up data_prep
docker wait data_prep
docker-compose ${ENVFILE} up random_forest
docker-compose stop
PAUSE