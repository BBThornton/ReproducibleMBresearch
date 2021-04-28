FROM qiime2/core:2020.8

WORKDIR /data_prep

RUN pip install pymongo
RUN pip install pandas
ADD data_prep.py .

ENV PYTHONPATH=/data_prep
