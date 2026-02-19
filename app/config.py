import logging
import os
from llm import get_llm
from sqlalchemy import create_engine
from langchain_community.utilities import SQLDatabase

# LLM setup
default_platform = os.getenv('DEFAULT_LLM_PLATFORM', 'LMSTUDIO_OPENAI')

flight_llm = get_llm(
    model_name=os.getenv('FLIGHT_LLM_MODEL', 'qwen/qwen3-30b-a3b-2507'),
    platform_name=os.getenv('FLIGHT_LLM_PLATFORM', default_platform),
)
luggage_llm = get_llm(
    model_name=os.getenv('LUGGAGE_LLM_MODEL', 'lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF'),
    platform_name=os.getenv('LUGGAGE_LLM_PLATFORM', default_platform),
)

# Database setup
URL = 'sqlite:///flights.db'
engine = create_engine(URL, echo=False)
db = SQLDatabase(engine)

# Maximum number of SQL generation attempts
MAX_ATTEMPTS = 3

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)
