import os
import argparse
import statistics

from utils.data_handlers import get_xml_files, load_data, get_gold_pairs, get_candidate_pairs, save_pairs


def create_pairs(data_path):
    # Get the filenames of only xml files
    filenames = get_xml_files(data_path)

    filenames.remove("31.xml")

    print("Found", len(filenames), "xml files")

    # Load data
    texts, events, tlinks = load_data(data_path, filenames)

    # Check outputs
    assert len(filenames) == len(texts) == len(events) == len(tlinks)

    # Get the gold pairs
    print("Extracting the gold pairs...")
    gold_pairs = get_gold_pairs(events, tlinks)

    print("Got gold pairs for", len(gold_pairs), "reports")
    print("Found", len(gold_pairs[0]), "gold pairs for the first report")
    assert len(gold_pairs[0]) == len(tlinks[0])

    # Statistics
    num_gold_pairs_test = []

    for p in gold_pairs:
        num_gold_pairs_test.append(len(p))

    print("The average number of gold pairs per report is", statistics.mean(num_gold_pairs_test))

    # Save pairs
    save_pairs(filenames, gold_pairs, "test_gold_pairs.xml", mode="gold")
    print("Saved gold pairs.")

    # Get the generated candidate pairs
    print("Generating the candidate pairs...")
    test_cnd_pairs = get_candidate_pairs(texts, events, tlinks)

    print("Got candidate pairs for", len(test_cnd_pairs), "reports")
    print("Found", len(test_cnd_pairs[0]), "candidate pairs for the first report")

    # Statistics
    num_cnd_pairs_test = []

    for p in test_cnd_pairs:
        num_cnd_pairs_test.append(len(p))

    print("The average number of candidate pairs per report is", statistics.mean(num_cnd_pairs_test))

    # Save pairs
    save_pairs(filenames, test_cnd_pairs, "test_candidate_pairs.xml", mode="candidate")
    print("Saved candidate pairs.")


if __name__ == '__main__':
    argParser = argparse.ArgumentParser()
    argParser.add_argument("-path", "--path", help="The path to the folder that contains the data files")

    args = argParser.parse_args()

    assert os.path.isdir(args.path)

    create_pairs(args.path)

