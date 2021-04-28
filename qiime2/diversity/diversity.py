import json
import os
from pymongoClient import client
import qiime2
import logging
from qiime2.plugins import diversity, metadata, feature_table, empress, emperor
import numpy as np

CURRENT_STAGE = "Diversity"


def alpha_diversity(sequences, metadata, metric, out_dirs):
    """
    Runs an alpha diversity anlyses using a combiantion of parameters
    :param sequences: The sequence table
    :param metadata: The metadata for the sequnces
    :param metric: The alpha diviersity scoring metric
    :param out_dirs: the output directories
    :return: NONE
    """
    alpha_diversity = diversity.pipelines.alpha(sequences, metric=metric)

    alpha_diversity.alpha_diversity.save(out_dirs[0])

    correlation = diversity.visualizers.alpha_group_significance(alpha_diversity.alpha_diversity,
                                                                 metadata)
    correlation.visualization.save(out_dirs[1])


def beta_diversity(distance_matrix, metadata, params, out_dirs):
    """
    Runs an beta diversity analyses using a combination of parameters
    :param distance_matrix: The distance matrix used for the diversity scoring
    :param metadata: The metadata for the samples
    :param params: The paramters for the function (passed exernal from container)
    :param out_dirs: The output directories for the data
    :return: NONE
    """
    params["distance_matrix"] = distance_matrix
    params["metadata"] = metadata.get_column("dx")
    # Beta diversity with relation to the diagnosis metadata
    dx_beta_diversity = diversity.visualizers.beta_group_significance(**params)
    dx_beta_diversity.visualization.save(out_dirs[2])


def empress_plot(parent_exp, sequence_table, scoring, tree, metadata, params, out_dirs):
    """
    Perfoms a number of stages to generate an empress plot. An empress plot contains a phlogenetic tree, PCoA anlyses,
    A biplot for the PCoA and related data about taxa frequency
    :param parent_exp: The parent experiment
    :param sequence_table: The sequences in table format
    :param scoring: The scoring system to use for the PCoA analyses
    :param tree: The phylogenetic tree of the samples
    :param metadata: The metadata of the samples
    :param params: The parameters passed externally from the docker container
    :param out_dirs: The output directories
    :return: NONE
    """
    # Classification file used in order to convert the UIDs to the taxonomic labels
    classification_file = db.get_specified_parent_stage("Feature_Classification", [parent_exp], [])["output"]["data"]
    classification = qiime2.Artifact.load(classification_file)

    relative_sequence = feature_table.methods.relative_frequency(sequence_table)
    # Pcoa biplot used for the empress plot
    pcoa_biplot = diversity.methods.pcoa_biplot(scoring, relative_sequence.relative_frequency_table)

    params["tree"] = tree
    params["pcoa"] = pcoa_biplot.biplot
    params["feature_table"] = relative_sequence.relative_frequency_table
    params["sample_metadata"] = metadata
    params["feature_metadata"] = classification.view(qiime2.Metadata)

    # Empress visual provides both the PCOA plots and the phylogenetic tree. Also shows important features
    # for PCOA positioning
    empress_plot = empress.visualizers.community_plot(**params)

    empress_plot.visualization.save(out_dirs[3])


def experiment(exp_id, parent_name, parameters):
    """
    Runs the experiment for this service which performs a series of diversity anlyses including;
    alpha diversity, beta diversity, PCoA and biplots
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

    # Metadata for the samples used in diversity metrics to determine importance
    metadata_file = db.get_specified_parent_stage("Metadata_Creator", [parent], [])["output"]["data"]
    sample_metadata = qiime2.Metadata.load(metadata_file)

    # Tree for all the phylogenic diversity metrics
    phylogenetic_tree_file = db.get_specified_parent_stage("Rooted_Tree", [parent], [])["output"]["data"]
    phylogenetic_tree = qiime2.Artifact.load(phylogenetic_tree_file)

    # The UID sequences to perform diversity analysis on
    sequences = qiime2.Artifact.load(parent["output"]["data"][1])

    diversity_metrics = diversity.pipelines.core_metrics_phylogenetic(table=sequences,
                                                                      phylogeny=phylogenetic_tree,
                                                                      sampling_depth=parameters["metrics_sampling_depth"],
                                                                      metadata=sample_metadata)

    alpha_diversity(sequences, sample_metadata, parameters["alpha_diversity_metric"], outputs)

    beta_diversity(diversity_metrics.weighted_unifrac_distance_matrix, sample_metadata, parameters["beta_diversity"].copy(),
                   outputs)

    empress_plot(parent, diversity_metrics.rarefied_table, diversity_metrics.weighted_unifrac_pcoa_results,
                 phylogenetic_tree, sample_metadata, parameters["pcoa"].copy(), outputs)

    this_experiment = {
        "_id": exp_id,
        "parent": parent_name,
        "stage": CURRENT_STAGE,
        "params": parameters,
        "output": {
            "data": outputs[0],
            "visuals": outputs[1:]
        }
    }

    db.new_experiment(this_experiment)


if __name__ == '__main__':
    db = client.dbClient()
    # Get the passed parameters
    experiment_id = os.getenv("EXP_ID")
    parent_experiment = os.getenv("PARENT")
    params_in = json.loads(os.getenv("PARAMS"))
    np.random.seed(params_in["random_seed"])


    print("Running " + experiment_id)
    experiment(experiment_id, parent_experiment, params_in)
    print("Closing Service")

    db.close()
