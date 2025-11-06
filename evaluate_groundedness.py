import os
import asyncio
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from typing import Any, Dict, List, Optional
import json
from pathlib import Path
from azure.ai.evaluation import evaluate
from azure.ai.evaluation import GroundednessEvaluator
from azure.ai.evaluation.simulator import Simulator
from azure.ai.evaluation import AzureOpenAIModelConfiguration
from openai import AzureOpenAI
import importlib.resources as pkg_resources
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

azure_ai_project = {
    "subscription_id": "", # AI Foundry project subscription ID
    "resource_group": "", # AI Foundry project resource group
    "workspace_name": "", # AI Foundry project name
}

# Standard Azure OpenAI Endpoint
azure_openai_endpoint = ""
# Name of the model deployment
azure_openai_deployment = ""
# API version, e.g., "2024-02-15-preview"
azure_openai_api_version = ""

model_config = AzureOpenAIModelConfiguration(
    azure_endpoint=azure_openai_endpoint,
    azure_deployment=azure_openai_deployment,
)


os.environ["AZURE_OPENAI_ENDPOINT"] = azure_openai_endpoint
os.environ["AZURE_DEPLOYMENT_NAME"] = azure_openai_deployment
os.environ["AZURE_API_VERSION"] = azure_openai_api_version

##################
# LOAD THE DATA

resource_name = "grounding.json"
package = "azure.ai.evaluation.simulator._data_sources"
conversation_turns = []

with pkg_resources.path(package, resource_name) as grounding_file, Path(grounding_file).open("r") as file:
    data = json.load(file)

for item in data:
    conversation_turns.append([item])
    if len(conversation_turns) == 2:
        break

##################
# TARGET ENDPOINT

def example_application_response(query: str, context: str) -> str:
    deployment = os.environ.get("AZURE_DEPLOYMENT_NAME")
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")

    if not deployment:
        raise ValueError("AZURE_DEPLOYMENT_NAME environment variable is not set")
    
    if not endpoint:
        raise ValueError("AZURE_OPENAI_ENDPOINT environment variable is not set")

    # Get a client handle for the AOAI model
    client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_version=os.environ.get("AZURE_API_VERSION"),
        azure_ad_token_provider=token_provider,
    )

    # Prepare the messages
    messages = [
        {
            "role": "system",
            "content": f"You are a user assistant who helps answer questions based on some context.\n\nContext: '{context}'",
        },
        {"role": "user", "content": query},
    ]
    # Call the model
    completion = client.chat.completions.create(
        model=deployment,
        messages=messages,  # type: ignore
        max_tokens=800,
        temperature=0.7,
        top_p=0.95,
        frequency_penalty=0,
        presence_penalty=0,
        stop=None,
        stream=False,
    )

    message = completion.to_dict()["choices"][0]["message"]
    if isinstance(message, dict):
        message = message["content"]
    return message

######################
# RUN THE SIMULATOR

async def custom_simulator_callback(
    messages: Dict,
    stream: bool = False,
    session_state: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
) -> dict:
    messages_list = messages["messages"]
    # get last message
    latest_message = messages_list[-1]
    application_input = latest_message["content"]
    context = latest_message.get("context", None)
    # call your endpoint or ai application here
    context_str = str(context) if context is not None else ""
    response = example_application_response(query=application_input, context=context_str)
    # we are formatting the response to follow the openAI chat protocol format
    message = {
        "content": response,
        "role": "assistant",
        "context": context,
    }
    messages["messages"].append(message)
    return {"messages": messages["messages"], "stream": stream, "session_state": session_state, "context": context}



async def main():
    custom_simulator = Simulator(model_config=model_config)

    outputs = await custom_simulator(
        target=custom_simulator_callback,
        conversation_turns=conversation_turns,
        max_conversation_turns=1,
        concurrent_async_tasks=10,
    )

    output_file = "ground_sim_output.jsonl"
    with Path(output_file).open("w") as file:
        for output in outputs:
            file.write(output.to_eval_qr_json_lines())

if __name__ == "__main__":
    asyncio.run(main())