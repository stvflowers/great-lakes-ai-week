import os
from azure.ai.projects import AIProjectClient
from azure.identity import InteractiveBrowserCredential
from azure.ai.agents.models import CodeInterpreterTool
from azure.ai.ml.entities import AzureAISearchConnection
from azure.ai.agents.models import AzureAISearchTool, AzureAISearchQueryType
from dotenv import load_dotenv
from azure.ai.ml import MLClient

# Load environment variables from .env file
load_dotenv()

# Create an Azure AI Client from an endpoint, copied from your Azure AI Foundry project.
# You need to login to Azure subscription via Azure CLI and set the environment variables
project_endpoint = os.getenv("PROJECT_ENDPOINT")  # Ensure the PROJECT_ENDPOINT environment variable is set
if project_endpoint is None:
    raise ValueError("The PROJECT_ENDPOINT environment variable must be set.")

model_deployment_name = os.getenv("MODEL_DEPLOYMENT_NAME")  # Ensure the MODEL_DEPLOYMENT_NAME environment variable is set
if model_deployment_name is None:
    raise ValueError("The MODEL_DEPLOYMENT_NAME environment variable must be set.")

# Create an AIProjectClient instance
project_client = AIProjectClient(
    endpoint=project_endpoint,
    credential=InteractiveBrowserCredential(),  # Use Azure Interactive Browser Credential for authentication
)

#################################################
# < Add an existing Azure AI Search connection > 
#################################################

my_connection_name = os.getenv("AI_FOUNDRY_WORKSPACE_SEARCH_CONNECTION_NAME")  # Ensure the AI_FOUNDRY_WORKSPACE_SEARCH_CONNECTION_NAME environment variable is set
if my_connection_name is None:  
    raise ValueError("The AI_FOUNDRY_WORKSPACE_SEARCH_CONNECTION_NAME environment variable must be set.")

my_endpoint = os.getenv("AI_SEARCH_ENDPOINT")  # Ensure the AI_SEARCH_ENDPOINT environment variable is set
if my_endpoint is None:
    raise ValueError("The AI_SEARCH_ENDPOINT environment variable must be set.")

my_key = os.getenv("AI_SEARCH_KEY")  # Ensure the AI_SEARCH_KEY environment variable is set
if my_key is None:
    raise ValueError("The AI_SEARCH_KEY environment variable must be set.")

my_connection = AzureAISearchConnection(
    name=my_connection_name,
    endpoint=my_endpoint,
    api_key=my_key
)

azure_ai_conn_id = project_client.connections.get(my_connection_name).id

index_name = os.getenv("AI_SEARCH_INDEX_NAME")  # Ensure the AI_SEARCH_INDEX_NAME environment variable is set
if index_name is None:
    raise ValueError("The AI_SEARCH_INDEX_NAME environment variable must be set.")

ai_search_tool = AzureAISearchTool(
    index_connection_id=azure_ai_conn_id,
    index_name=index_name,
    query_type=AzureAISearchQueryType.VECTOR_SEMANTIC_HYBRID,
    top_k=3,
    filter="",
)

####################################################
#  </ Add an existing Azure AI Search connection >
#####################################################


with project_client:
    # Create an agent with the Bing Grounding tool
    agent = project_client.agents.create_agent(
        model=model_deployment_name,  # Model deployment name
        name="my-azure-agent",  # Name of the agent
        instructions="""
        # OBJECTIVE
            You are an agent which uses your knowledge stores to help users.
            You have access to an Azure AI Search index which you can use to answer user queries.
        
        # PERSONA
            You are a helpful assistant.
        
        # TOOLS
            You have access to the following tool: Azure AI Search. Use it to answer user queries.
            When using the tool, be sure to use the most specific search terms possible.
        """,  # Instructions for the agent
        tools=ai_search_tool.definitions,  # Attach the tool
        tool_resources=ai_search_tool.resources,  # Attach the tool resources
    )
    print(f"Created agent, ID: {agent.id}")

    # Create a thread for communication
    thread = project_client.agents.threads.create()
    print(f"Created thread, ID: {thread.id}")
    
    # Add a message to the thread
    message = project_client.agents.messages.create(
        thread_id=thread.id,
        role="user",  # Role of the message sender
        content="What is Azure Frogger?",  # Message content
    )
    print(f"Created message, ID: {message['id']}")
    
    # Create and process an agent run
    run = project_client.agents.runs.create_and_process(thread_id=thread.id, agent_id=agent.id)
    print(f"Run finished with status: {run.status}")
    
    # Check if the run failed
    if run.status == "failed":
        print(f"Run failed: {run.last_error}")
    
    # Fetch and log all messages
    messages = project_client.agents.messages.list(thread_id=thread.id)
    for message in messages:
        print(f"Role: {message.role}, Content: {message.content}")
    
    # Delete the agent when done
    # project_client.agents.delete_agent(agent.id)
    # print("Deleted agent")