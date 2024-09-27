# Analysing zero-shot temporal relation extraction on clinical notes using temporal consistency

This repo contains the code used in our paper to perform zero-shot 
temporal relation extraction and the LLMs' raw responses.

------

## Abstract

This paper presents the first study for temporal relation extraction in a zero-shot setting focusing on biomedical text. 
We employ two types of prompts and five LLMs (GPT-3.5, Mixtral, Llama 2, Gemma, and PMC-LLaMA) to obtain responses about the temporal relations between two events. 
Our experiments demonstrate that LLMs struggle in the zero-shot setting performing worse than fine-tuned specialized models in terms of F1 score, showing that this is a challenging task for LLMs.
We further contribute a novel comprehensive temporal analysis by calculating consistency scores for each LLM. Our findings reveal that LLMs face challenges in providing responses consistent to the temporal properties of uniqueness and transitivity. Moreover, we study the relation between the temporal consistency of an LLM and its accuracy and whether the latter can be improved by solving temporal inconsistencies. 
Our analysis shows that even when temporal consistency is achieved, the predictions can remain inaccurate.

-----

## Requirements

You can install the requirements for the code by running 
``pip install -r requirements.txt`` in your python virtual environment.
If you are using conda, run 
``conda env create -f environment.yml`` to create the ``temp_env`` 
environment with the required packages.


## Data

We used the test data created for the 2012 Informatics for Integrating
Biology and the Bedside (i2b2) challenge for Clinical Records.
You can find the dataset [here](https://portal.dbmi.hms.harvard.edu/projects/n2c2-nlp/).
First, you need to create an account and then, you can download the data from 
the "2012 Temporal Relations Challenge Downloads" section.

When the data is obtained, in order to create the gold and candidate pairs of events, 
and then their union, for all the xml files in a folder, run the following scripts 
with the path to the folder as input:
```
python data_preparation.py -path /path/to/the/data/folder 
python create_union_pairs.py -path /path/to/the/data/folder
```

The generated pairs will be saved in xml format in the current directory.
We provide the pairs for the test set of the i2b2 dataset in 
the "test_gold_pairs.xml", "test_candidate_pairs.xml", and "gold_and_candidate_pairs.xml" files.


## Zero-shot BioTempRE

The code for running the prompts and obtaining LLMs' responses can be found in the 
"llm_requests" folder. You can add your "api_key" in the "connection.py" script and then, 
run "main.py" with your specified parameters 
(run ``python main.py --help`` for a detailed list of the arguments).
The responses will be saved in the path provided in the form of 
json files, one json file per report.

[comment]: <> (## Temporal consistency and evaluation)



------

## Acknowledgments
This research has been funded by the Vienna Science and Technology 
Fund (WWTF)[10.47379/VRG19008] ”Knowledge-infused Deep Learning for Natural Language Processing”.