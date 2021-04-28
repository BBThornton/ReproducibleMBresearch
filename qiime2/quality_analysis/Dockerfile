FROM qiime2/core:2020.8

WORKDIR /qiime_qa
RUN pip install pymongo
ADD qiime_qa.py .
ENV PYTHONPATH=/qiime_qa
