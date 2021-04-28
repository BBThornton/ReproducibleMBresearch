FROM qiime2/core:2020.8

WORKDIR /qiime_rooted_tree
RUN pip install pymongo
ADD rooted_tree.py .

ENV PYTHONPATH=/qiime_rooted_tree
