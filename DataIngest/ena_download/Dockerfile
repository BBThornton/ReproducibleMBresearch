FROM python:3.8

WORKDIR /ena_download

RUN pip install pymongo


ADD DataIngest/ena_download/ena_download.py .

ENV PYTHONPATH=/ena_download

