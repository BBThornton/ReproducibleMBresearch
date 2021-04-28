import ast
import json
import os
from pymongoClient import client
import qiime2
import logging
import pandas as pd
import pathlib
import tempfile

CURRENT_STAGE = "Machine_Learning_Data_Prep"


def extract_csvs(viz):
    """
    Function will extract the raw data from a visualisation, prevents the need for recomputing data
    to display in another no qiime2 form
    :param viz: The qiime2 artifact file
    :return:
    """
    data = []
    # create a temp dir to work in, that way we don't have
    # to manually clean up, later
    with tempfile.TemporaryDirectory() as temp:
        # export the `data` directory from the visualization
        viz.export_data(temp)
        temp_pathlib = pathlib.Path(temp)
        # iterate through all of the files that we just extracted above
        for file in temp_pathlib.iterdir():
            # if the file is a csv file, copy it to the final dest
            if file.suffix == '.tsv':
                data.append(pd.read_csv(file, sep="\t", header=0, index_col=0))
    return data


def experiment(exp_id, parent_name, parameters):
    """
    Runs the experiment for this service which quality controls the input samples using the defined parameters
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
    # Get the parent information
    parents = ast.literal_eval(os.getenv("PARENT_NAMES"))

    # Collect the file output locations from the database (based on the default locations of the services)
    outputs = db.default_result_output_loc(CURRENT_STAGE, os.getenv("OUTPUT_DIR"))

    df = pd.DataFrame()
    # Will get all the data information from the parents to combine into one dataframe
    for item in parents:
        parent = db.get_one({"_id": item[0]}, "experiment")
        if parent is None:
            logging.warning("Parent experiment does not exist - Maybe it hasn't finished executing")
            return

        # Outputs of the current parent
        stage_outputs = db.get_one({"_id": parent["stage"]}, "services")["output"]["data"]

        # Get the exact ouput required
        if parent["output"]["data"] is list:
            data = parent["output"]["data"][stage_outputs.index(item[1])]
        else:
            data = parent["output"]["data"]

        # Will always get the sample metadata first
        if parents.index(item) == 0:
            metadata_file = db.get_specified_parent_stage("Metadata_Creator", [parent], [])["output"]["data"]

            df = pd.read_csv(metadata_file, sep="\t", header=0, index_col=0)
            df = df.dropna(subset=[params["classifier_column"]])
            df = df[params["classifier_column"]]

        # If the file is an aritfact extract the relevant data to a dataframe
        if data[-4:] == ".qza":
            artifact = qiime2.Artifact.load(data)
            temp = extract_csvs(artifact)
            df = pd.merge(left=df, left_index=True, right=temp[0], right_index=True, how='inner')

        # If the data frame is a tsv then will import as dataframe
        elif data[-4:] == ".tsv":

            if parent["stage"] == "Freq_To_Biom":
                temp = pd.read_csv(data, sep="\t", header=None)
                temp = temp.drop(index=0)
                temp = temp.T
                temp = temp.set_index(temp.columns[0])
                temp.columns = temp.iloc[0]
                temp = temp.iloc[1:]
                # Merge the current data with this data
                df = pd.merge(left=df, left_index=True, right=temp, right_index=True, how='inner')

        # Filter a table based on lefse results
        elif data[-4:] == ".res":
            temp = pd.read_csv(data, sep="\t", header=None)
            filtered = temp[temp[2].isin(["CD", "UC", "Healthy"])]
            filtered[0] = filtered[0].str.replace('.', ';')
            filter = list(filtered[0])
            # Create a list of regex filtering terms
            for item in filter:
                item = item + "[;__]*"
            filter.append("dx")
            # Will filter all the dataframe to only the taxa covered by the lefse regex
            filterreg = "|".join(filter)

            df = df.filter(regex=filterreg, axis=1)

    # Save the combined data to a csv file
    df.to_csv(outputs[0], sep = ',')

    this_experiment = {
        "_id": experiment_id,
        "parent": None,
        "stage": CURRENT_STAGE,
        "params": parameters,
        "output": {
            "data": outputs[0]
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
