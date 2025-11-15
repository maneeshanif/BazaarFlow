
import os 
import logging


logger = logging.getLogger(__name__)

from agents import AsyncOpenAI, OpenAIChatCompletionsModel
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())


api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    logger.warning(
        "GEMINI_API_KEY not set; using placeholder key. Real agent calls will fail until a valid key is configured."
    )
    api_key = "placeholder-test-key"

# Use environment variables for external LLM client configuration
external_client = AsyncOpenAI(
    api_key=api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

model = OpenAIChatCompletionsModel(
    model=os.getenv("OPENAI_MODEL", "gemini-2.0-flash"),
    openai_client=external_client,
)