FROM qiime2/core:2020.8

WORKDIR /qiime_data_import
RUN pip install pymongo
ADD qiime_data_import.py .
ENV PYTHONPATH=/qiime_data_import
