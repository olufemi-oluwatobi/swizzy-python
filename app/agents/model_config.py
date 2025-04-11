import os
from openai import AsyncOpenAI
from agents import OpenAIChatCompletionsModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup OpenAI client for Gemini
api_key = os.getenv("GOOGLE_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL")

if not api_key or not base_url:
    raise ValueError("Missing required environment variables: GOOGLE_API_KEY and OPENAI_BASE_URL must be set")

# Create custom OpenAI client
client = AsyncOpenAI(
    api_key=api_key,
    base_url=base_url
)

# Create the model configuration for Gemini
gemini_model = OpenAIChatCompletionsModel(
    model="gemini-2.0-flash",
    openai_client=client,
)
