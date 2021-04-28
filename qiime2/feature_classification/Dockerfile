FROM qiime2/core:2020.8

WORKDIR /qiime_classifier
RUN pip install pymongo
ADD feature_classification.py .
ENV PYTHONPATH=/qiime_classifier
