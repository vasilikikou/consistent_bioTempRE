from typing import List, Dict
import os
import re
import json

from llm_requests.strategies.common import generate_questions, initialize_result_dict
from llm_requests.connection import send_prompt


def generate_prompt(
    doc: str, doc_name: str, candidate_pairs: List[Dict], relations_scheme: List[str]
):
    all_prompts = []

    # Generate preamble with the documents text + the instruction for the model
    preamble = f"""Input document D:

{doc}
----------------------
Given document D, answer the following questions ONLY with Yes or No.
"""

    # Generate prompt for each pair of candidate
    for idx, pair in enumerate(candidate_pairs):
        tlinkID = pair["tlinkID"]
        from_id = pair["fromID"]
        to_id = pair["toID"]

        event_1 = pair["fromText"]
        event_2 = pair["toText"]
        questions = generate_questions(relations_scheme, event_1, event_2)
        questions = [f"Q{idx+1}: " + q for idx, q in enumerate(questions)]
        prompt_info = (
            preamble
            + " \n ".join(questions)
            + "\n Each line should contain an answer, e.g. 'A1: yes'. Make sure the output format is matched exactly."
        )

        all_prompts.append(
            {
                "prompt_info": prompt_info,
                "num_questions": len(questions),
                "pair_idx": idx,
                "pair": pair,
                "doc_name": doc_name,
                "unique_id": f"{doc_name}_{from_id}_{to_id}",
            }
        )

    return all_prompts


def extract_answer(resp):
    question_id = int(resp[0]) - 1
    answer = resp[1]
    answer = answer.strip().lower()
    if "yes" in answer and "no" not in answer:
        return question_id, "yes"
    elif "no" in answer and "yes" not in answer:
        return question_id, "no"
    else:
        return question_id, "unsure"


def transform_response(response: str, num_answers: int):
    answers = re.findall(r"A(\d+): (.*?)$", response, flags=re.MULTILINE)
    answers = dict(map(extract_answer, answers))
    if len(answers) != num_answers:
        raise ValueError("Number of answers does not match number of questions.")

    answers = [answers[i] for i in range(num_answers)]
    return answers


def process_query(
    query: Dict, api_hyperparams: Dict, save_dir: str, max_tries: int = None
):
    prompt = query["prompt_info"]
    unique_id = query["unique_id"]
    save_file = os.path.join(save_dir, f"{unique_id}.json")

    # check cache or initialize
    if os.path.exists(save_file):
        with open(save_file, "r") as file:
            results = json.load(file)
    else:
        # set initial values
        results = initialize_result_dict(query)

    if results["finished"]:
        return results
    elif max_tries is not None and results["num_tries"] >= max_tries:
        return results

    try:
        messages = [
            {
                "role": "user",
                "content": prompt,
            }
        ]
        response_text = send_prompt(messages, api_hyperparams)
        results["messages"] = messages
        results["responses"] = [response_text]

        # process answer
        results["answers"] = transform_response(
            response_text, num_answers=query["num_questions"]
        )

        # extract info
        # results["completion_tokens"] = completion_tokens
        # results["prompt_tokens"] = prompt_tokens
        # results["total_tokens"] = total_tokens

        # mark as finished
        results["finished"] = True

    except Exception as ex:
        results["errors"][results["num_tries"]] = str(ex)

    # count tries, in case we want to account for API errors etc.
    results["num_tries"] += 1

    # save
    # with open(save_file, "w") as file:
    #     json.dump(results, file, indent=4)
    return results