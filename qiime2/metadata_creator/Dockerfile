FROM python:3.8

WORKDIR /metadata_creator

RUN pip install pymongo

ADD metadata_creator.py .

ENV PYTHONPATH=/metadata_creator
