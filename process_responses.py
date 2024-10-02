import os
import json
import argparse
import xml.etree.ElementTree as ET

from utils.data_handlers import load_pairs
from xml.etree.ElementTree import Element, SubElement, ElementTree


def process(method_name: str, responses_path: str, data_path: str, processed_responses_path: str):
    # Create folders to save the responses
    gold_path = os.path.join(processed_responses_path, method_name + "_gold_predictions")
    cnd_path = os.path.join(processed_responses_path, method_name + "_candidate_predictions")

    if not os.path.exists(gold_path):
        os.makedirs(gold_path)

    if not os.path.exists(cnd_path):
        os.makedirs(cnd_path)

    # Read the files
    json_files = os.listdir(responses_path)

    # Check that all files are in json format
    for f in json_files:
        if not f.endswith(".json"):
            print(f)
        assert f.endswith(".json")

    # Check that all the files are there
    reports = list(set([f.split("_")[0] + ".xml" for f in json_files]))
    assert len(reports) == 119

    # Load the gold
    gold_pairs = load_pairs(os.path.join(data_path, "test_gold_pairs.xml"), reports)
    gold_pair_ids = {}
    gold_ids = {}
    for p, f in zip(gold_pairs, reports):
        gold_pair_ids[f] = []
        gold_ids[f] = []
        for pair in p:
            gold_pair_ids[f].append((pair["fromID"], pair["toID"]))
            gold_ids[f].append(pair["tlinkID"])

    # Load the candidates
    cnd_pairs = load_pairs(os.path.join(data_path, "test_candidate_pairs.xml"), reports)
    cnd_pair_ids = {}
    cnd_ids = {}
    for p, f in zip(cnd_pairs, reports):
        cnd_pair_ids[f] = []
        cnd_ids[f] = []
        for pair in p:
            cnd_pair_ids[f].append((pair["fromID"], pair["toID"]))
            cnd_ids[f].append(pair["tlinkID"])

    relations = ["BEFORE", "AFTER", "INCLUDES", "IS INCLUDED", "SIMULTANEOUS"]

    # Read the json files for each pair of each report
    errored_gold = []
    for r, report_id in enumerate(gold_pair_ids):
        root = Element("TAGS")
        for i, g_ids in enumerate(gold_pair_ids[report_id]):
            json_f = report_id.replace(".xml", "") + "_" + g_ids[0] + "_" + g_ids[1] + ".json"
            if json_f in json_files:
                with open(os.path.join(responses_path, json_f)) as json_file:
                    json_data = json.load(json_file)
                    # print(json_data)
                # Extract response
                answers = json_data["answers"]

                # if list(set(answers)) == ["no"] or list(set(answers)) == [-1]:
                if "yes" not in answers:
                    pred_relations = ["None"]
                else:
                    indices = [i for i, x in enumerate(answers) if x == "yes"]
                    pred_relations = [relations[ind] for ind in indices]

                if list(set(answers)) == [-1]:
                    errored_gold.append([report_id, gold_pairs[r][i]["fromID"], gold_pairs[r][i]["toID"]])
                    print("Found all -1 in", report_id, "for events", gold_pairs[r][i]["fromID"], ",", gold_pairs[r][i]["toID"])

                for rel in pred_relations:
                    tlink = {"id": gold_pairs[r][i]["tlinkID"],
                             "fromID": gold_pairs[r][i]["fromID"],
                             "fromText": gold_pairs[r][i]["fromText"],
                             "toID": gold_pairs[r][i]["toID"],
                             "toText": gold_pairs[r][i]["toText"],
                             "type": rel}
                    # print(tlink)
                    tlink_elem = SubElement(root, 'TLINK', tlink)
            else:
                print(json_f, "not found")
        tree = ElementTree(root)
        tree.write(os.path.join(gold_path, report_id))

    print("Found errors in", len(errored_gold), "responses for gold pairs")

    errored_cnd = []
    for r, report_id in enumerate(cnd_pair_ids):
        root = Element("TAGS")
        for i, cnd_ids in enumerate(cnd_pair_ids[report_id]):
            json_f = report_id.replace(".xml", "") + "_" + cnd_ids[0] + "_" + cnd_ids[1] + ".json"
            if json_f in json_files:
                with open(os.path.join(responses_path, json_f)) as json_file:
                    json_data = json.load(json_file)
                    # print(json_data)
                # Extract response
                answers = json_data["answers"]

                # if list(set(answers)) == ["no"] or list(set(answers)) == [-1]:
                if "yes" not in answers:
                    pred_relations = ["None"]
                else:
                    indices = [i for i, x in enumerate(answers) if x == "yes"]
                    pred_relations = [relations[ind] for ind in indices]

                if list(set(answers)) == [-1]:
                    errored_cnd.append([report_id, cnd_pairs[r][i]["fromID"], cnd_pairs[r][i]["toID"]])
                    print("Found all -1 in", report_id, "for events", cnd_pairs[r][i]["fromID"], ",", cnd_pairs[r][i]["toID"])

                for rel in pred_relations:
                    tlink = {"id": cnd_pairs[r][i]["tlinkID"],
                             "fromID": cnd_pairs[r][i]["fromID"],
                             "fromText": cnd_pairs[r][i]["fromText"],
                             "toID": cnd_pairs[r][i]["toID"],
                             "toText": cnd_pairs[r][i]["toText"],
                             "type": rel}
                    tlink_elem = SubElement(root, 'TLINK', tlink)
            else:
                print(json_f, "not found")
        tree = ElementTree(root)
        tree.write(os.path.join(cnd_path, report_id))

    print("Found errors in", len(errored_cnd), "responses for candidate pairs")


if __name__ == "__main__":
    argParser = argparse.ArgumentParser()

    argParser.add_argument("-method", "--method", help="The name of the LLM and prompting strategy used")
    argParser.add_argument("-responses", "--resp_path", help="The path to the folder where the json response "
                                                             "files are saved")
    argParser.add_argument("-data", "--data_path", help="The path where the gold and candidate pairs xml files "
                                                        "are saved")
    argParser.add_argument("-results", "--results_path", help="The path to save the processed responses")

    args = argParser.parse_args()

    process(method_name=args.method,
            responses_path=args.resp_path,
            data_path=args.data_path,
            processed_responses_path=args.results_path
            )
