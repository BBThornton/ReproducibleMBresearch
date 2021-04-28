import json
import os
from os import path
import logging
from pymongoClient import client

CURRENT_STAGE = "Metadata_Creator"


def get_samples_from_manifest(manifest_experiment):
    """
    Get a list of all the samples that are being imported into qiime2. This is based on the parent experiment manifest
    creator
    :param manifest_experiment: The experiment that is being used as the parent (an instance of manifest creator)
    :type manifest_experiment: dict (experiment instance)
    :return: A list of sample ids that are present in the manifest file
    :rtype: list
    """
    print(manifest_experiment)
    # Get the sample Id for the given manifest
    samples = []
    sample_manifest = manifest_experiment["output"]["data"]
    # Get the sampleIds from the manifest
    with open(sample_manifest, "r") as f:
        for line in f:
            split = line.split("\t")
            samples.append(split[0])
    return samples


def write_metadata_manifest(output_loc, samples):
    """
    Writes a metdsata manifest file for qiime2. Makes the assumption that all samples have the same metadata headers.
    This is a requirement for qiime2. Different metadata could be combined in future releases
    :param output_loc: file location for the manifest file
    :type output_loc: str
    :param samples: a list of sample ids (run accession)
    :type samples: list
    :return: None
    """
    # Prepare the output file headings
    output_file = open(output_loc, "w")
    output_file.write("sample-id \t")

    # Write the headers of the meatadata data
    if "selection" in params:
        # If a selection of specific metadata is given get those headers
        db_selection = params["selection"]
        headings = list(db_selection.keys())
        db_selection["_id"] = 0
        db_selection["sample"] = 0
        for item in headings:
            output_file.write(item + "\t")
    else:
        # Get all the headers of the samples
        db_selection = {"_id": 0, "sample": 0}
        sample_alias = db.get_one_selective({"run_accession": samples[1]}, {"_id": 0}, "samples")["sample_alias"]
        headings = db.get_one_selective({"sample": sample_alias}, {"_id": 0}, "metadata").keys()
        [output_file.write(heading + "\t") for heading in list(headings)[1:]]

    output_file.write("\n")

    # For every sample Id get the metdata and write to file
    for id in samples[1:]:
        # Need to convert from the run accession to the sample alias in the metadata
        # This might not be needed for all datasets so a more flexibile method may be needed
        sample_alias = db.get_one_selective({"run_accession": id}, {"sample_alias": 1}, "samples")["sample_alias"]
        metadata = db.get_one_selective({"sample": sample_alias}, db_selection, "metadata")
        output_file.write(id + "\t")
        # This shouldnt happen but for some datasets metadata may be removed from repository so account for that
        if metadata is None:
            [output_file.write("NaN\t") for item in list(headings)[1:]]
            output_file.write("\n")

        else:
            for value in metadata.values():
                # If no value for the header in the metadata replace with NaN
                if value is not None:
                    output_file.write(value + "\t")
                else:
                    output_file.write("NaN\t")
            output_file.write("\n")


def experiment(exp_id, parent_name, parameters):
    """
    Runs the experiment for this service which creates a file containing all the metadata for the samples in a manifest
    file
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

    samples = get_samples_from_manifest(parent)
    write_metadata_manifest(outputs[0], samples)

    this_experiment = {
        "_id": experiment_id,
        "parent": parent_name,
        "stage": CURRENT_STAGE,
        "params":parameters,
        "output": {
            "visuals": None,
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
