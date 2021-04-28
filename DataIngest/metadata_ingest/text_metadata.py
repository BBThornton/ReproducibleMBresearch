import json
import os

from pymongoClient import client
import pandas as pd
import numpy as np


def import_data(file, header=1, nan_val=' ', separator=','):
    """
    Will import the metadata objects into the database
    :param file: The file containing the metadata
    :param header: val of 1 headers are first line in file, val of -1 headers are in the first column of the file
    :param nan_val: The value of empty items in the file
    :param separator: The sperator of the itmes in the file
    :return:
    """
    if header == 1:
        df = pd.read_csv(file, sep=separator, header=header)
    elif header == -1:
        df = pd.read_csv(file, sep=separator, header=None)
        df = df.T
        headers = df.iloc[0, :]
        df.columns = headers
        df = df.iloc[1:, :]

    # Replace nan values
    df = df.replace(nan_val, np.NaN)

    # Export to json for db entry
    json_data = df.to_json(orient="records")

    return json.loads(json_data)


if __name__ == '__main__':
    metadata_file = os.getenv('META_FILE')
    data = import_data(metadata_file, -1, separator="\t")
    db_client = client.dbClient()
    for item in data:
        db_client.insert_one(item,"metadata")
    db_client.close()