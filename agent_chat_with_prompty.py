import os
from datetime import datetime
from dotenv import load_dotenv
from azure.identity import InteractiveBrowserCredential
from azure.ai.projects import AIProjectClient
from opentelemetry.instrumentation.openai_v2 import OpenAIInstrumentor
from opentelemetry import trace
from azure.monitor.opentelemetry import configure_azure_monitor


# Set the variable to include input and output content in telemetry
os.environ["OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"] = "true"
# Instrument OpenAI SDK for telemetry
OpenAIInstrumentor().instrument()

now = datetime.now()
timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

# Fake user identifier for telemetry
user_id = "bandit.heeler@archaeology.au"

# Load environment variables from .env file
load_dotenv()

# Create an Azure AI Client from an endpoint, copied from your Azure AI Foundry project.
project_endpoint = os.getenv("PROJECT_ENDPOINT")  # Ensure the PROJECT_ENDPOINT environment variable is set
if project_endpoint is None:
    raise ValueError("The PROJECT_ENDPOINT environment variable must be set.")

model_deployment_name = os.getenv("MODEL_DEPLOYMENT_NAME")  # Ensure the MODEL_DEPLOYMENT_NAME environment variable is set
if model_deployment_name is None:
    raise ValueError("The MODEL_DEPLOYMENT_NAME environment variable must be set.")

ai_foundry_agent_id = os.getenv("AI_FOUNDRY_AGENT_ID")  # Ensure the AI_FOUNDRY_AGENT_ID environment variable is set
if ai_foundry_agent_id is None:
    raise ValueError("The AI_FOUNDRY_AGENT_ID environment variable must be set.")

# Create an AIProjectClient instance
project_client = AIProjectClient(
    endpoint=project_endpoint,
    credential=InteractiveBrowserCredential(),  # Use Azure Interactive Browser Credential for authentication
)

#################################
### TELEMETRY SETUP ############
### Get the connection string from the project client and configure Azure Monitor
app_insights_connection_string = project_client.telemetry.get_application_insights_connection_string()
configure_azure_monitor(connection_string=app_insights_connection_string)
#################################


##############################################
### TRACE AN OPEN AI CLIENT REQUEST ##########
##############################################
client = project_client.get_openai_client()

response = client.chat.completions.create(
    model=model_deployment_name,
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is Azure Frogger?"},
    ],
)

print(f"Role: {response.choices[0].message.role}, Content: {response.choices[0].message.content}")



