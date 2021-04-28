"""
The following system was used to create two niave bayes classifiers
for the two Silva reference datbases. This must
be run inside a qiime2 container an example definition is provided
This is an extremely resource intensive process and can take
in excess of 7 hours, and use 42 GB of ram

The classifiers created during this process have been provided in
the one drive link
https://1drv.ms/u/s!Aus7JUVmM6BTgbsirlMW6ddWK-bn7Q?e=wNHBJD
"""

import qiime2
from qiime2.plugins.feature_classifier.methods import extract_reads,  fit_classifier_naive_bayes

# Import the refernce database files
seqs = qiime2.Artifact.import_data("FeatureData[Sequence]","99_Silva_111_rep_set.fasta")
taxa = qiime2.Artifact.import_data("FeatureData[Taxonomy]","99_Silva_111_taxa_map.txt")
seqs138 = qiime2.Artifact.load("silva-138-99-seqs.qza")
taxa138 = qiime2.Artifact.load("silva-138-99-tax.qza")

#Create and save the classifiers
classifier =  fit_classifier_naive_bayes(seqs,taxa,verbose = True)
classifier.classifier.save("Silva_111")
classifier = fit_classifier_naive_bayes(seqs138,taxa138,verbose = True)
classifier.classifier.save("Silva_138")