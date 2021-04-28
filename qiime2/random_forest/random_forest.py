import os
from pymongoClient import client
import pandas as pd
import json
from pymongoClient import client
import seaborn as sns
import logging
from sklearn.preprocessing import StandardScaler, label_binarize
import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score

## Sklearn Libraries
from sklearn.model_selection import StratifiedKFold
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV, cross_val_predict

from sklearn.metrics import f1_score, confusion_matrix, roc_curve, auc, \
    classification_report, recall_score, precision_recall_curve

from sklearn.metrics import average_precision_score

"""
Process for training a random forest model for the classification of microbiome samples
Uses pre formatted data form a data formatting system.
"""

CURRENT_STAGE = "Random_Forest"


def plot_prec_recall(labels, predictedtargets, definitions, outputStruct, out_dir):
    """
    Plot a precision recal graph for the passed data
    :param labels: The actual labels of the data classified
    :param predictedtargets: The predicted taregets from the classifier
    :param definitions: The definitions of the data
    :param outputStruct: The output dictionary for data summary
    :param out_dir: The outpur directory
    :return: NONE
    """
    precision = dict()
    recall = dict()
    average_precision = dict()
    y_bin = label_binarize(labels, classes=list(range(labels.nunique())))
    for i in range(labels.nunique()):
        precision[i], recall[i], _ = precision_recall_curve(y_bin[:, i],
                                                            predictedtargets[:, i])
        average_precision[i] = average_precision_score(y_bin[:, i], predictedtargets[:, i])

    # Plot the averaged precision recall of all the classes
    precision["macro"], recall["macro"], _ = precision_recall_curve(y_bin.ravel(),
                                                                    predictedtargets.ravel())
    average_precision["macro"] = average_precision_score(y_bin, predictedtargets,
                                                         average="macro")

    # Store the information ready for file output
    outputStruct["average_precision"] = average_precision["macro"]
    outputStruct["precision"] = precision["macro"].tolist()
    outputStruct["recall"] = recall["macro"].tolist()

    fig = plt.figure()

    plt.plot(recall['macro'], precision['macro'],
             label='macro-average precision score curve (area = {0:0.2f})'
                   ''.format(average_precision["macro"]), linestyle=':', )

    # Plot the precision recall curve of each subclass
    colors = ['blue', 'red', 'green']
    for i, color in zip(range(labels.nunique()), colors):
        plt.plot(recall[i], precision[i], color=color, lw=2,
                 label='Precision-recall for class {0} (area = {1:0.2f})'
                       ''.format(definitions[i], average_precision[i]))

    plt.xlabel('Recall')
    plt.ylabel('Precision')
    plt.ylim([0.0, 1.05])
    plt.xlim([0.0, 1.0])
    plt.legend(loc="lower center", bbox_to_anchor=(0.5, -0.6))
    fig.subplots_adjust(bottom=0.35)
    plt.savefig(out_dir)
    plt.clf()


def plot_roc(labels, predictions, definitions, outputStruct, out_dir):
    """
    Plots an area under curve graph
    :param labels: The actual labels of the data classified
    :param predictedtargets: The predicted taregets from the classifier
    :param definitions: The definitions of the data
    :param outputStruct: The output dictionary for data summary
    :param out_dir: The outpur directory
    :return: NONE
    """
    # Calcualte the datapoints to be plotted
    fpr = dict()
    tpr = dict()
    roc_auc = dict()
    y_bin = label_binarize(labels, classes=list(range(labels.nunique())))

    for i in range(labels.nunique()):
        fpr[i], tpr[i], _ = roc_curve(y_bin[:, i], predictions[:, i])
        roc_auc[i] = auc(fpr[i], tpr[i])

    fpr["macro"], tpr["macro"], _ = roc_curve(y_bin.ravel(), predictions.ravel())
    roc_auc["macro"] = roc_auc_score(y_bin, predictions, average="macro")

    # Store the information ready for file output
    outputStruct["roc_auc"] = roc_auc["macro"]
    outputStruct["mean_fpr"] = fpr["macro"].tolist()
    outputStruct["mean_trp"] = tpr["macro"].tolist()

    # Plot the average of all the classes
    plt.plot(fpr["macro"], tpr["macro"],
             label='macro-average ROC curve (area = {0:0.2f})'
                   ''.format(roc_auc["macro"]),
             color='navy', linestyle=':', linewidth=4)

    # Plot each class
    colors = ['blue', 'red', 'green']
    for i, color in zip(range(labels.nunique()), colors):
        plt.plot(fpr[i], tpr[i], color=color,
                 label='ROC curve of class {0} (area = {1:0.2f})'
                       ''.format(definitions[i], roc_auc[i]))
    plt.plot([0, 1], [0, 1], 'k--')
    plt.xlim([0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('Receiver operating characteristic for multi-class data')
    plt.legend(loc="lower right")
    plt.savefig(out_dir)
    plt.clf()


def plot_confusion_matrix(predictions, actual, out_dir):
    """
    Plots a confusion matrix of the classifications
    :param predictions: The predictions of the model
    :param actual: The actual labels of the samples
    :param out_dir: The output directory for the image
    :return:
    """
    fig = plt.figure()
    cm = pd.DataFrame(confusion_matrix(actual, predictions), columns=["CD", "UC", "Healthy"],
                      index=["CD", "UC", "Healthy"])
    sns.heatmap(cm, annot=True)
    plt.savefig(out_dir)


def run_classification(features, labels, definitions, outputStruct, out_dirs, parameters):
    """
    Runs the random forest classification plotting a number of figures (ROC, Precision recall and confusion matrix)
    :param features: The features of the data (X)
    :param labels: The actual labels of the data classified
    :param definitions: The definitions of the data
    :param outputStruct: The output dictionary for data summary
    :param out_dirs:The outpur directory
    :param random_state:the random state for the crossfold
    :return: The prediction labels and the actual labels
    """

    # Stratified kfold to counteract teh class imbalances
    cv = StratifiedKFold(**parameters["k_fold"])

    # Create a random fores model
    model = RandomForestClassifier(**parameters["rf_classifier"])

    # Fit the model to the data
    fitted = model.fit(features, labels)
    predictions = cross_val_predict(model, features, labels, cv=cv, method="predict_proba")

    predictions_labels = cross_val_predict(model, features, labels, cv=cv)

    feature_importances = pd.DataFrame(fitted.feature_importances_,
                                       index=features.columns,
                                       columns=['importance']).sort_values('importance', ascending=False)

    plot_roc(labels, predictions, definitions, outputStruct, out_dirs[1])
    plot_prec_recall(labels, predictions, definitions, outputStruct, out_dirs[2])

    # Store the individual feature importance ready for writing to file
    outputStruct["feature_importances"] = feature_importances.to_dict('index')

    return predictions_labels, labels


def experiment(exp_id, parent_name, parameters):
    """
    Runs the experiment for this service which trains and tests a random forest model with kfold cross validation
    Additionally it produces an AUROC and precision recall curve in addition to a confusuion matrix
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

    dataset = pd.read_csv(parent["output"]["data"], sep=',', index_col=0, header=0)

    output_file = open(outputs[0], "w")

    # Used as a json for writing summary stats to a file
    outputStruct = dict()

    # Convert the string classifications to integers
    factor = pd.factorize(dataset["dx"])
    # Shows the mapping of sample id to new integer label
    dataset.dx = factor[0]
    # List of order of the diganosis labels
    definitions = factor[1]

    # Splitting the data into independent and dependent variables
    X = dataset.iloc[:, 1:]
    y = dataset.iloc[:, 0]

    predicted_targets, actual_targets = run_classification(X, y, definitions, outputStruct, outputs, parameters)

    plot_confusion_matrix(predicted_targets, actual_targets, outputs[3])

    # Will store the samples precicted and actual classification, in addition do sperating those that were classified
    # incorrectly
    wrong_samples = []
    all_samples = []
    indexs = actual_targets.index
    for i in range(len(predicted_targets)):
        all_samples.append({"sample_id": indexs[i], "predicted": definitions[predicted_targets[i]],
                            "actual": definitions[actual_targets[i]]})
        if predicted_targets[i] != actual_targets[i]:
            wrong_samples.append({"sample_id": indexs[i], "predicted": definitions[predicted_targets[i]],
                                  "actual": definitions[actual_targets[i]]})
    outputStruct["classifications"] = all_samples
    outputStruct["incorrect_samples"] = wrong_samples

    # Write the data summary to file
    json.dump(outputStruct, output_file, indent=4)

    this_experiment = {
        "_id": experiment_id,
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

    experiment_id = os.getenv("EXP_ID")
    parent_experiment = os.getenv("PARENT")
    params = json.loads(os.getenv("PARAMS"))

    print("Running " + experiment_id)
    experiment(experiment_id, parent_experiment, params)
    print("Closing Service")

    db.close()
