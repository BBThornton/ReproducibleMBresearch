import json
import os
import logging
from pymongoClient import client
import qiime2
from qiime2.plugins import feature_classifier, metadata

CURRENT_STAGE = "Feature_Classification"


def experiment(exp_id, parent_name, parameters):
    """
    Runs the experiment for this service which gives a taxonomy to the ASV's determined during quality analyses
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

    # Loads the sequences and a classifier reference database model
    sequences = qiime2.Artifact.load(parent["output"]["data"][1])

    gg_classifier = qiime2.Artifact.load("/qiime_classifier/classifiers/" + params["classifier"] + ".qza")

    # Prepare the parameters for the classification process
    classify_params = parameters["classify_sklearn"].copy()
    classify_params["reads"] = sequences
    classify_params["classifier"] = gg_classifier

    # Classification runner
    taxonomy = feature_classifier.methods.classify_sklearn(**classify_params)

    # Artifact save
    taxonomy.classification.save(outputs[0])

    # Visual save
    taxonomy_classification = metadata.visualizers.tabulate(taxonomy.classification.view(qiime2.Metadata))
    taxonomy_classification.visualization.save(outputs[1])

    this_experiment = {
        "_id": experiment_id,
        "parent": parent_name,
        "stage": CURRENT_STAGE,
        "params":parameters,
        "output": {
            "data": outputs[0],
            "visuals": outputs[1]
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
