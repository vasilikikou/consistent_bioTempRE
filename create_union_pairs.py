import os
import argparse
import statistics
import xml.etree.ElementTree as ET

from xml.etree.ElementTree import Element, SubElement, ElementTree
from utils.data_handlers import load_pairs, load_cnd_pairs, filter_unique_pairs


def create_union(test_path):
    filenames = os.listdir(test_path)
    filenames.remove("31.xml")

    # Load the gold
    gold_pairs = load_pairs("test_gold_pairs.xml", filenames)
    gold_pair_ids = {}
    gold_ids = {}
    for p, f in zip(gold_pairs, filenames):
        gold_pair_ids[f] = []
        gold_ids[f] = []
        for pair in p:
            gold_pair_ids[f].append((pair["fromID"], pair["toID"]))
            gold_ids[f].append(pair["tlinkID"])

    # Load the candidates
    cnd_pairs = load_pairs("test_candidate_pairs.xml", filenames)
    cnd_pair_ids = {}
    cnd_ids = {}
    for p, f in zip(cnd_pairs, filenames):
        cnd_pair_ids[f] = []
        cnd_ids[f] = []
        for pair in p:
            cnd_pair_ids[f].append((pair["fromID"], pair["toID"]))
            cnd_ids[f].append(pair["tlinkID"])

    # Find overlap
    reports_overlap = []
    for gold_p_ids, cnd_p_ids in zip(list(gold_pair_ids.values()), list(cnd_pair_ids.values())):
        overlap = []
        # print(len(list(set(gold_pairs) & set(cnd_pairs))))
        for gp in gold_p_ids:
            for cp in cnd_p_ids:
                if gp == cp:  # or (gp[0] == cp[1] and gp[1] == cp[0]):
                    overlap.append(gp)
        reports_overlap.append(len(overlap))

    print("The average number of overlap between the gold and candidate pairs per report is",
          statistics.mean(reports_overlap))

    # Create union
    union_report_pairs = []
    for report_gpairs, report_cpairs in zip(gold_pairs, cnd_pairs):
        report_pairs = report_gpairs + report_cpairs
        union_report_pairs.append(filter_unique_pairs(report_pairs))

    pairs_sum = []
    for r in union_report_pairs:
        pairs_sum.append(len(r))

    print(sum(pairs_sum))

    # Save union
    root = Element("Pairs")
    for filename, pairs in zip(filenames, union_report_pairs):
        report_element = SubElement(root, "Report", {"filename": filename})
        counter = 0
        for p in pairs:
            pair_element = SubElement(report_element, "Pair", {"char_span_start": f'{p["char_span_start"]}',
                                                               "char_span_end": f'{p["char_span_end"]}',
                                                               "tlinkID": p["tlinkID"],
                                                               "fromID": p["fromID"],
                                                               "fromText": p["fromText"],
                                                               "fromStart": p["fromStart"],
                                                               "fromEnd": p["fromEnd"],
                                                               "toID": p["toID"],
                                                               "toText": p["toText"],
                                                               "toStart": p["toStart"],
                                                               "toEnd": p["toEnd"]})
            counter += 1
    tree = ElementTree(root)
    tree.write("gold_and_candidate_pairs.xml")


if __name__ == '__main__':
    argParser = argparse.ArgumentParser()
    argParser.add_argument("-path", "--path", help="The path to the folder that contains the data files")

    args = argParser.parse_args()

    assert os.path.isdir(args.path)

    create_union(args.path)
