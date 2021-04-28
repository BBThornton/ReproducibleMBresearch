import io
import os
import logging
import json
import pandas as pd
from pymongoClient import client
import qiime2
from qiime2.plugins import taxa, feature_table
import biom


CURRENT_STAGE = "Freq_To_Biom"


def new_headers(df, metadata):
    """
    Creates a set of overview headers according to the requirements of Qiime2 and Lefse biom format
    :param df: The dataframe to use for new headers
    :param metadata: The diagnosis metadata to add
    :return: The new headers
    """
    result = [('#Diagnosis', '#OTU id')]
    current = df.columns
    for i in current[1:]:
        result.append((metadata[i], i))
    return result

def experiment(exp_id, parent_name, parameters):
    """
    Runs the experiment for this service which converts the frequency tables from the frequency table service into
    csv/biom format. This also adds the condition information for each sample. This can then be used to import into
    lefse and machine learning services without having to reference the metadata file directly.
    :param exp_id: The id of this experiment (must not already exist in the database)
    :type exp_id: str
    :param parent_name: Id of the parent experiment (should be of the correct stage type (data input)) and must exits
    :type parent_name: str
    :param parameters: The parameters for the experiment itself (dictionary of params)
    :type parameters: dict
    :return: NONE
    """

    # Check if an experiment using this id already exists
    if db.check_doc_exists({"_id": exp_id}, "experiment"):
        logging.warning("That experiment_id already exists, please use a new experiment ID")
        return

    # Get the parent experiment information from the db
    parent = db.stage_parent_correct(CURRENT_STAGE, parent_name)

    if parent is None:
        logging.warning("Parent experiment does not exist - Maybe it hasn't finished executing")
        return

    # Collect the file output locations from the database (based on the default locations of the services)
    outputs = db.default_result_output_loc(CURRENT_STAGE, os.getenv("OUTPUT_DIR"))

    taxa_table = qiime2.Artifact.load(parent["output"]["data"][0])

    otu_freq = feature_table.methods.relative_frequency(taxa_table)

    # Convert the table into a dataframe (pandas)
    biom_table = otu_freq.relative_frequency_table.view(biom.Table)
    df = pd.read_csv(io.StringIO(biom_table.to_tsv()), sep='\t', header=1)
    samples = df.columns.values.tolist()[1:]

    meta_data = {}
    # Add the condition status directly to the table information
    for id in samples:
        metadata_id = db.get_one_selective({"run_accession": id}, {"sample_alias": 1, "_id": 0}, "samples")[
            "sample_alias"]
        condition = db.get_one_selective({"sample": metadata_id}, {"dx": 1, "_id": 0}, "metadata")
        # Capture when the condition is not included in the metadata
        if condition is not None:
            meta_data[id] = condition["dx"]
        else:
            meta_data[id] = "inconclusive"

    df.columns = pd.MultiIndex.from_tuples(new_headers(df, meta_data))

    df = df.drop(' ', axis=1, level=0)

    df = df.drop('inconclusive', axis=1, level=0)

    # Save the dataframe to a .csv file
    df.to_csv(outputs[0], sep='\t', index=False)

    this_experiment = {
        "_id": experiment_id,
        "parent": parent_name,
        "stage": CURRENT_STAGE,
        "params":parameters,
        "output": {
            "data": outputs[0],
            "visuals": None
        }
    }

    db.new_experiment(this_experiment)


if __name__ == '__main__':
    db = client.dbClient()

    # Get the passed parameters
    experiment_id = os.getenv("EXP_ID")
    parent_experiment = os.getenv("PARENT")
    params = json.loads(os.getenv("PARAMS"))

    print("Running " + experiment_id)
    experiment(experiment_id, parent_experiment, params)
    print("Closing Service")

    db.close()
