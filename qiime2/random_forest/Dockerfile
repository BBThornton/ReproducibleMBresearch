FROM python:3.8

WORKDIR /random_forest

RUN pip install pymongo
RUN pip install pandas
RUN pip install sklearn
RUN pip install matplotlib
RUN pip install seaborn
ADD random_forest.py .

ENV PYTHONPATH=/random_forest
