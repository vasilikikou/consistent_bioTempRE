from typing import Dict

# import backoff  # for exponential backoff -> to avoid RateLimitError
import openai
from huggingface_hub import InferenceClient


def send_llama_prompt(messages, hyperparams: Dict):

    prompt = f"""[INST]<<SYS>><</SYS>>{messages[0]['content']}[/INST]"""
    for message in messages[1:]:
        if message["role"] == "assistant":
            prompt += f"""{message['content']}"""
        else:
            prompt += f"""[INST]{message['content']}[/INST]"""
            
    client = InferenceClient(model=hyperparams["url"])
    full_response = client.text_generation(
        prompt=prompt,
        max_new_tokens=600,
        # details=True,
        temperature=hyperparams["temp"],
        do_sample=True,
    )

    generated_text = full_response#.generated_text
    # completion_tokens = full_response.completion_tokens
    # prompt_tokens = full_response.prompt_tokens
    # total_tokens = full_response.total_tokens

    return generated_text


def send_prompt(messages, hyperparams: Dict):
    if hyperparams["model"] in ["meta-llama/Llama-2-70b-chat-hf"]:
        return send_llama_prompt(messages, hyperparams)

    if hyperparams["model"] in ["mistralai/Mixtral-8x7B-Instruct-v0.1"]:
        client = openai.Client(base_url=f"http://localhost:8080/v1", api_key="EMPTY")
    else:
        client = openai.Client()
    response = client.chat.completions.create(
        model=hyperparams["model"],
        messages=messages,
        temperature=hyperparams["temp"],
        # request_timeout=1
    )
    response_text = response.choices[0].message.content
    completion_tokens = response.usage.completion_tokens
    prompt_tokens = response.usage.prompt_tokens
    total_tokens = response.usage.total_tokens

    return response_text

