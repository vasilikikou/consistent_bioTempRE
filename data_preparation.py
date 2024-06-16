import os
import argparse
import statistics

from utils.data_handlers import get_xml_files, load_data, get_gold_pairs, get_candidate_pairs, save_pairs


def create_pairs(test_path):
    # Get filenames
    test_files = get_xml_files(test_path)

    test_files.remove("31.xml")

    print("Found", len(test_files), "xml files for the test set")

    # Load data
    test_texts, test_events, test_tlinks = load_data(test_path, test_files)

    # Check outputs
    assert len(test_files) == len(test_texts) == len(test_events) == len(test_tlinks)

    # Get the gold pairs
    print("Extracting gold pairs...")
    test_gold_pairs = get_gold_pairs(test_events, test_tlinks)

    print("Got gold pairs for", len(test_gold_pairs), "reports")
    print("Found", len(test_gold_pairs[0]), "gold pairs for the first report")
    assert len(test_gold_pairs[0]) == len(test_tlinks[0])

    # Statistics
    num_gold_pairs_test = []

    for p in test_gold_pairs:
        num_gold_pairs_test.append(len(p))

    print("The average number of gold pairs per report in the test set is", statistics.mean(num_gold_pairs_test))

    # Save pairs
    save_pairs(test_files, test_gold_pairs, "test_gold_pairs.xml", mode="gold")
    print("Saved gold pairs.")

    # Get the generated candidate pairs
    print("Generating the candidate pairs...")
    test_cnd_pairs = get_candidate_pairs(test_texts, test_events, test_tlinks)

    print("Got candidate pairs for", len(test_cnd_pairs), "reports")
    print("Found", len(test_cnd_pairs[0]), "candidate pairs for the first report")

    # Statistics
    num_cnd_pairs_test = []

    for p in test_cnd_pairs:
        num_cnd_pairs_test.append(len(p))

    print("The average number of candidate pairs per report in the test set is", statistics.mean(num_cnd_pairs_test))

    # Save pairs
    save_pairs(test_files, test_cnd_pairs, "test_candidate_pairs.xml", mode="candidate")
    print("Saved candidate pairs.")


if __name__ == '__main__':
    argParser = argparse.ArgumentParser()
    argParser.add_argument("-path", "--path", help="The path to the folder that contains the data files")

    args = argParser.parse_args()

    assert os.path.isdir(args.path)

    create_pairs(args.path)

