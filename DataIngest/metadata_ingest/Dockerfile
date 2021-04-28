FROM python:3.8

WORKDIR /metadata_ingest

RUN pip install pymongo
RUN pip install pandas
RUN pip install numpy

ADD  DataIngest/metadata_ingest/text_metadata.py .

ENV PYTHONPATH=/metadata_ingest

