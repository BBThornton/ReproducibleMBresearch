from __future__ import absolute_import
import os
import subprocess
import json
import logging
import os

"""
Due to LEfSe being coded primarily in python 2 many of the individual file are called using the subprocess system
"""

subprocess.call(
    ['pip','install','pymongo'])
from pymongoClient import client

CURRENT_STAGE = "Lefse"

def experiment(exp_id, parent_name, parameters):
    """
    Runs the experiment for this service which uses lefse to determine the discrimant taxa for each classifation
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

    # Separate the outputs into visuals and data (NEEDED AS PYTHON 2.7 handles the output retrieval differently)
    visuals_out = []
    data_out = []
    for item in outputs:
        if "Visuals" in item:
            visuals_out.append(item)
        else:
            data_out.append(item)

    # The UID sequences to perform diversity analysis on
    table = parent["output"]["data"]
    with open(data_out[0], 'w') as filtered:
        with open(table, 'r') as f:
            for line in f:
                new_line = line.replace(";", "|")
                filtered.writelines(new_line)
    filtered.close()
    f.close()

    # Format the data from qiime2 to Lefse formatting
    subprocess.call(
        ['format_input.py', data_out[0], data_out[1], '-c', '1', '-u', '2', '-o',
         '1000000'])
    # Run lefse analyses on the formatted data
    subprocess.call(
        ['run_lefse.py', data_out[1],data_out[2]])
    # Plot a Lefse barplot using the results
    subprocess.call(['plot_res.py', data_out[2], visuals_out[0]])
    # Plot a cladogram from the results
    subprocess.call(
        ['plot_cladogram.py', data_out[2], visuals_out[1],
         '--format', 'svg'])


    this_experiment = {
        "_id": experiment_id,
        "parent": parent_name,
        "stage": CURRENT_STAGE,
        "params": parameters,
        "output": {
            "data": data_out,
            "visuals": visuals_out
        }
    }

    db.new_experiment(this_experiment)

if __name__ == '__main__':
    db = client.dbClient()

    experiment_id = os.getenv("EXP_ID")
    parent_experiment = os.getenv("PARENT")
    params = json.loads(os.getenv("PARAMS"))

    print("Running " + experiment_id)
    experiment(experiment_id, parent_experiment, params)
    print("Closing Service")

    db.close()