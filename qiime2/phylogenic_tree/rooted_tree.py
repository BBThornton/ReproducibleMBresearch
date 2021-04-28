import json
import os
import logging
from pymongoClient import client
import qiime2
from qiime2.plugins import alignment, phylogeny

CURRENT_STAGE = "Rooted_Tree"

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

    # Get the representative sequences from the QA experiment
    representative_sequences = qiime2.Artifact.load(parent["output"]["data"][1])

    # Run a series of steps to create a phylogenetic tree file
    mafft_alignment = alignment.methods.mafft(representative_sequences)
    masked_mafft_alignment = alignment.methods.mask(mafft_alignment.alignment)
    unrooted_tree = phylogeny.methods.fasttree(masked_mafft_alignment.masked_alignment)
    rooted_tree = phylogeny.methods.midpoint_root(unrooted_tree.tree)

    rooted_tree.rooted_tree.save(outputs[0])

    this_experiment = {
        "_id": experiment_id,
        "parent": parent_name,
        "stage": CURRENT_STAGE,
        "params":parameters,
        "output": {
            "data": outputs[0]
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
