FROM qiime2/core:2020.8

WORKDIR /qiime_alpha_diversity
RUN apt-get update
RUN apt-get install build-essential -y

RUN pip install pymongo
RUN pip install empress
ADD diversity.py .
ENV PYTHONPATH=/qiime_alpha_diversity
