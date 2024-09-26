from typing import List, Tuple


# generate questions according to the relation schema
def generate_questions(relations_scheme: List, event_1: str, event_2: str) -> List[str]:
    """Generate questions for the prompts"""
    questions = []
    for relation in relations_scheme:
        if relation == "BEFORE":  # (ent_1, BEFORE, ent_2)
            questions.append(
                f"Did '{event_1}' start before '{event_2}' started and end before '{event_2}' ended?"
            )
        elif relation == "AFTER":  # (ent_1, AFTER, ent_2)
            questions.append(
                f"Did '{event_1}' start after '{event_2}' started and end after '{event_2}' ended?"
            )
        elif relation == "OVERLAP":  # (ent_1, OVERLAP, ent_2)
            questions.append(
                f"Did '{event_1}' and '{event_2}' happen at the same time or one include the other?"
            )
        elif relation == "INCLUDES":  # (ent_1, INCLUDES, ent_2)
            questions.append(
                f"Did '{event_2}' start and end while '{event_1}' was happening?"
            )
        elif relation == "IS INCLUDED":  # (ent_1, IS INCLUDED, ent_2)   !!!
            questions.append(
                f"Did '{event_1}' start and end while '{event_2}' was happening?"
            )
        elif relation == "SIMULTANEOUS":  # (ent_1, SIMULTANEOUS, ent_2)
            questions.append(
                f"Did '{event_1}' and '{event_2}' start and end at the same time?"
            )
        else:
            raise ValueError(
                f"Unknown relation {relation} which is not in the current relation scheme {relations_scheme}"
            )

    questions = [f"{q} Answer with Yes or No." for q in questions]
    return questions


def initialize_result_dict(query):
    return {
        "query": query,
        "messages": [],
        "responses": [],
        "answers": [-1] * query["num_questions"],
        "completion_tokens": 0,
        "prompt_tokens": 0,
        "total_tokens": 0,
        "errors": {},
        "num_tries": 0,
        "finished": False,
    }