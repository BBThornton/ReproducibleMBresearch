FROM qiime2/core:2020.8

WORKDIR /realtive_frequency_to_biom
RUN pip install pymongo
ADD frequency_artifact_to_biom.py .

ENV PYTHONPATH=/realtive_frequency_to_biom
