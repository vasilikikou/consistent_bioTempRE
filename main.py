import argparse
import os
from typing import Dict

from multiprocessing import Pool

from llm_requests.data import get_xml_files, load_data, load_pairs

import llm_requests.strategies.batchqa as batchqa
import llm_requests.strategies.cot as cot


def main(
    data_path: str,
    pairs_path: str,
    save_path: str,
    strategy: str,
    curr_relations_schema: Dict,
    API_HYPERPARAMS: Dict,
    debug: bool = False,
):

    # Load data
    print("Loading data")
    # Get filenames
    files = get_xml_files(data_path)
    files.remove("31.xml")

    # Run on a subset
    if debug:
        files = files[:2]

    file_ids = [file.replace(".xml", "") for file in files]

    # Load the document
    texts, events, tlinks = load_data(data_path, files)

    # Check the output
    assert len(files) == len(texts) == len(events) == len(tlinks)

    union_pairs = load_pairs(pairs_path, files)

    if strategy == "batchqa":
        generate_prompt = batchqa.generate_prompt
        process_query = batchqa.process_query
    elif strategy == "cot":
        generate_prompt = cot.generate_prompt
        process_query = cot.process_query

    print("Generating prompts")
    all_prompts = []
    for i in range(len(texts)):
        prompts = generate_prompt(
            doc_name=file_ids[i],
            doc=texts[i],
            candidate_pairs=union_pairs[i],
            relations_scheme=curr_relations_schema,
        )
        all_prompts.extend(prompts)

    # if strategy == "batchqa":
    #     process_query = batchqa.process_query
    # elif strategy == "cot":
    #     process_query = cot.process_query

    tmp_path = os.path.join(save_path, "tmp")
    print(tmp_path)
    os.makedirs(tmp_path, exist_ok=True)
    args_list = [(prompt, API_HYPERPARAMS, tmp_path, 2) for prompt in all_prompts]
    if debug:
        args_list = args_list[:6]

    print(f"Starting {len(args_list)} queries")
    num_processes = 3 if debug else API_HYPERPARAMS["num_processes"]
    with Pool(processes=num_processes) as pool:
        results = pool.starmap(process_query, args_list)

    print("Finished the queries")
    print(f"Saving {len(results)} results")
    # print(results)
    # TODO: save in Vasiliki format


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data_path",
        type=str,
        help="Path to the folder that contains the xml data files",
        default=""
    )
    parser.add_argument(
        "--path",
        type=str,
        help="Path to the project directory",
        default="",
    )
    parser.add_argument(
        "--temp", type=float, help="Temperature for the model", default=0.2
    )
    parser.add_argument(
        "--model", type=str, help="Model to use", default="gpt-3.5-turbo-1106"
    )
    parser.add_argument(
        "--strategy", type=str, help="Strategy to use: batchqa or cot", default="batchqa"
    )
    parser.add_argument(
        "--url", type=str, help="URL for the model", default="http://localhost:8000/"
    )
    parser.add_argument(
        "--save_path", type=str, help="Path to save the results", default="batchqa"
    )
    parser.add_argument(
        "--num_processes", type=int, help="Number of processes to use", default=150
    )
    parser.add_argument("--debug", type=bool, help="Debug mode", default=False)
    # num processes
    args = parser.parse_args()

    data_path = args.data_path

    path = args.path
    pairs_path = os.path.join(path, "gold_and_candidate_pairs.xml")
    save_path = args.save_path
    os.makedirs(save_path, exist_ok=True)

    API_HYPERPARAMS = {
        "model": args.model,
        "url": args.url,
        "temp": args.temp,
        "num_processes": args.num_processes,
    }

    curr_relations_schema = [
        "BEFORE",
        "AFTER",
        "INCLUDES",
        "IS INCLUDED",
        "SIMULTANEOUS",
    ]

    main(
        data_path=data_path,
        pairs_path=pairs_path,
        save_path=args.save_path,
        strategy=args.strategy,
        curr_relations_schema=curr_relations_schema,
        API_HYPERPARAMS=API_HYPERPARAMS,
        debug=args.debug,
    )
