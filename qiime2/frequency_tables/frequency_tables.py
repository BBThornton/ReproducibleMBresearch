import json
import os
from pymongoClient import client
import qiime2
from qiime2.plugins import taxa, feature_table
import logging

CURRENT_STAGE = "Frequency_Tables"


def experiment(exp_id, parent_name, parameters):
    """
    Runs the experiment for this service which creates a number of frequency and relative frequency tables with both
    classified an non classified ASV's.
    It also produces a number of summary visuals and a stacked barplot demonstrating the composition of all the samples.
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

    # Get the sequences from the feature classifcation service
    sequences = qiime2.Artifact.load(parent["output"]["data"])

    # Get the ASV information from the QA service
    reference_table_data = db.get_specified_parent_stage("Quality_Analysis", [parent], [])["output"]["data"][0]
    reference_table = qiime2.Artifact.load(reference_table_data)

    # Collect the file output locations from the database (based on the default locations of the services)
    outputs = db.default_result_output_loc(CURRENT_STAGE, os.getenv("OUTPUT_DIR"))

    # Create the taxa table
    taxa_table = taxa.methods.collapse(table=reference_table,
                                       taxonomy=sequences,
                                       level=params["level"])

    # Getting the relative frequency
    id_freq = feature_table.methods.relative_frequency(reference_table)
    otu_freq = feature_table.methods.relative_frequency(taxa_table.collapsed_table)

    # Save the table data
    taxa_table.collapsed_table.save(outputs[0])
    reference_table.save(outputs[1])
    otu_freq.relative_frequency_table.save(outputs[2])
    id_freq.relative_frequency_table.save(outputs[3])

    # Create visual summaries for every table
    feature_table.visualizers.summarize(reference_table).visualization.save(outputs[4])
    feature_table.visualizers.summarize(taxa_table.collapsed_table).visualization.save(outputs[5])
    feature_table.visualizers.summarize(id_freq.relative_frequency_table).visualization.save(outputs[6])
    feature_table.visualizers.summarize(otu_freq.relative_frequency_table).visualization.save(outputs[7])

    # Metadata for the samples used in diversity metrics to determine importance
    metadata_file = db.get_specified_parent_stage("Metadata_Creator", [parent], [])["output"]["data"]
    sample_metadata = qiime2.Metadata.load(metadata_file)

    # Visualise a stacked barplot for all samples
    stacked_boxplot = taxa.visualizers.barplot(reference_table, sequences, sample_metadata)
    stacked_boxplot.visualization.save(outputs[8])

    this_experiment = {
        "_id": experiment_id,
        "parent": parent_name,
        "stage": CURRENT_STAGE,
        "params": parameters,
        "output": {
            "data": outputs[0:5],
            "visuals": outputs[5:]
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
