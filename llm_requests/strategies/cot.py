from typing import List, Dict
import os
import json

from llm_requests.strategies.common import generate_questions, initialize_result_dict
from llm_requests.connection import send_prompt


def generate_prompt(
    doc: str,
    doc_name: str,
    candidate_pairs: List[Dict],
    relations_scheme: List,
):
    all_prompts = []

    # generate preamble
    preamble = f"""Input document D:

{doc}
----------------------
"""

    # generate prompt for each pair of candidate
    for idx, pair in enumerate(candidate_pairs):
        event_1 = pair["fromText"]
        event_2 = pair["toText"]

        from_id = pair["fromID"]
        to_id = pair["toID"]

        doc_text_prompt = (
            preamble
            + f" Given the document D, are '{event_1}' and '{event_2}' referring to the same event? Answer ONLY with Yes or No."
        )

        question_prompts = generate_questions(relations_scheme, event_1, event_2)

        prompts = {
            "doc_text_prompt": doc_text_prompt,
            "question_prompts": question_prompts,
        }

        all_prompts.append(
            {
                "prompt_info": prompts,
                "num_questions": len(question_prompts),
                "pair": pair,
                "pair_idx": idx,
                "doc_name": doc_name,
                "unique_id": f"{doc_name}_{from_id}_{to_id}",
            }
        )

    return all_prompts


def extract_answer(response_text):
    response_text = response_text.split("\n")[0]
    if "yes" in response_text and "no" not in response_text:
        return "yes"
    elif "no" in response_text and "yes" not in response_text:
        return "no"
    else:
        return -1


def process_query(
    query: Dict, api_hyperparams: Dict, save_dir: str, max_tries: int = None
):
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
        doc_text_prompt = query["prompt_info"]["doc_text_prompt"]
        question_prompts = query["prompt_info"]["question_prompts"]

        responses = []
        messages = [{"role": "user", "content": doc_text_prompt}]
        # print(json.dumps(messages, indent=4))
        response_text = send_prompt(messages, api_hyperparams)
        responses.append(response_text)

        is_same_event = extract_answer(response_text)
        if is_same_event == "yes":
            question_prompts = [
                "In that event, " + prompt[:1].lower() + prompt[1:]
                for prompt in question_prompts
            ]

        answers = []

        for question in question_prompts:
            messages.append({"role": "assistant", "content": response_text})
            messages.append({"role": "user", "content": question})

            response_text = send_prompt(messages, api_hyperparams)

            responses.append(response_text)
            answers.append(extract_answer(response_text.lower()))

        messages.append({"role": "assistant", "content": response_text})
        # fill results dict
        results["messages"] = messages
        results["responses"] = responses
        results["answers"] = answers

        # mark as finished
        results["finished"] = True

    except Exception as ex:
        results["errors"][results["num_tries"]] = str(ex)

    # count tries, in case we want to account for API errors etc.
    results["num_tries"] += 1

    # save
    with open(save_file, "w") as file:
        json.dump(results, file)
    return results
