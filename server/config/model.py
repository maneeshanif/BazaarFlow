from dotenv import load_dotenv
from agents import AsyncOpenAI,OpenAIChatCompletionsModel
import os
load_dotenv()


external_client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_API_BASE"),
)

model  = OpenAIChatCompletionsModel(
    model="gemini-2.0-flash",
    client=external_client,
)