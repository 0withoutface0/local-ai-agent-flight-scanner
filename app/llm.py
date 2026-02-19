import os
from langchain_ollama import ChatOllama
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

def get_llm(model_name, platform_name="OLLAMA"):
    if platform_name == "OLLAMA":
        return ChatOllama(
            model=model_name,
            temperature=0.2,
        )
    elif platform_name == "GROQ":
        return ChatGroq(
            temperature=1,
            model=model_name,
            groq_api_key=os.getenv("GROQ_API_KEY")
        )
    elif platform_name == "LMSTUDIO_OPENAI":
        return ChatOpenAI(
            model=model_name,
            temperature=0.2,
            api_key=os.getenv("LMSTUDIO_API_KEY", "lm-studio"),
            base_url=os.getenv("LMSTUDIO_OPENAI_BASE_URL", "http://127.0.0.1:1234/v1"),
        )

    raise ValueError(f"Unsupported platform_name: {platform_name}")
