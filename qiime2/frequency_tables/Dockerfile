FROM qiime2/core:2020.8

WORKDIR /qiime_frequency_tables
RUN pip install pymongo
RUN pip install sklearn
RUN pip install seaborn
ADD frequency_tables.py .

ENV PYTHONPATH=/qiime_frequency_tables
