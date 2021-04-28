import json
import os
import logging
from pymongoClient import client

CURRENT_STAGE = "Manifest_Creator"


def get_sample_locations(criteria):
    """
    Get the location of the sample files from the system. These are stored when the sample downloader is used but
    can also be added manually.
    Certain criteria in this function may need to be customised for individual studies
    :param criteria: The criteria for sample selection
    :type criteria: dict
    :return: The file locations of the selected samples
    :rtype: list
    """
    docs = []
    # Get the relevant sample information
    samples = db.query(criteria, 'samples')
    # Checks that the samples selected have valid metadata including diagnosis (This is valid for only this metadata)
    # A more generic approach could be developed in the future
    for sample in samples:
        try:
            if db.get_one({"sample": sample['sample_alias']}, 'metadata')['dx'] is not None:
                docs.append(sample)
        except Exception as error:
            logging.log(4,error)
    return docs


def write_manifest(sample_data, manifest_output_dir):
    """
    Write the manifest file in the qiime2 format
    :param sample_data: The samples that need to be included in the manifest file
    :param manifest_output_dir: Output location of the manifest file
    :return:
    """

    with open(manifest_output_dir, 'w') as f:
        f.write('sample-id\tabsolute-filepath\n')
        for sample in sample_data:
            line = sample['run_accession'] + '\t' + \
                   "/qiime_data_import/" + sample['file_location'][2:] + "/" + sample['run_accession'] + '.fastq.gz'
            f.write(line + '\n')


def experiment(exp_id, parent_name, parameters):
    """
    Runs the experiment for this service which collection information about a number of samples and writes a qiime2
    manifest file for data importing
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

    samples = os.getenv('SAMPLES')

    # Collect the file output locations from the database (based on the default locations of the services)
    outputs = db.default_result_output_loc(CURRENT_STAGE, os.getenv("OUTPUT_DIR"))

    # Get the sample information and write to the manifest file
    docs = get_sample_locations(json.loads(samples))
    write_manifest(docs, outputs[0])

    this_experiment = {
        "_id": experiment_id,
        "parent": parent_name,
        "stage": CURRENT_STAGE,
        "params": parameters,
        "output": {
            "visuals": None,
            "data": outputs[0]
        }

    }

    db.new_experiment(this_experiment)


if __name__ == '__main__':
    db = client.dbClient()

    experiment_id = os.getenv('EXP_ID')
    parent_experiment = os.getenv("PARENT")
    params = os.getenv("PARAMS")

    print("Running "+experiment_id)
    experiment(experiment_id,parent_experiment,params)
    print("Closing Service")

    db.close()
