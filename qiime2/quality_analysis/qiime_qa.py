import json
import os
from pymongoClient import client
import qiime2
from qiime2.plugins import quality_filter, deblur, feature_table, metadata, demux, cutadapt, dada2
import logging

# Name of current Stage constant
CURRENT_STAGE = "Quality_Analysis"


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

    # Get the parent experiment information from the db
    parent = db.stage_parent_correct(CURRENT_STAGE, parent_name)

    if parent is None:
        logging.warning("Parent experiment does not exist - Maybe it hasn't finished executing")
        return

    # Collect the file output locations from the database (based on the default locations of the services)
    outputs = db.default_result_output_loc(CURRENT_STAGE, os.getenv("OUTPUT_DIR"))

    # Get the sequence information from the parent
    sequences = qiime2.Artifact.load(parent["output"]["data"])

    # Run the dada2 denoise method
    dd2 = dada2.methods.denoise_pyro(sequences, 200, max_len=600, trunc_q=25, n_threads=0)

    # Save the neccessary information to the system file storage (mounted volume)
    dd2.table.save(outputs[0])
    dd2.representative_sequences.save(outputs[1])
    dd2.denoising_stats.save(outputs[2])
    demux.visualizers.summarize(sequences).visualization.save(outputs[3])
    feature_table.visualizers.summarize(dd2.table).visualization.save(outputs[4])

    # Save the experiment instance in the db
    this_experiment = {
        "_id": exp_id,
        "parent": parent_name,
        "stage": CURRENT_STAGE,
        "params": parameters,
        "output": {
            "data": outputs[0:3],
            "visuals": outputs[3:]
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
