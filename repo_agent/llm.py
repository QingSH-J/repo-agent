from langchain_deepseek import ChatDeepSeek
from dotenv import load_dotenv
import os


def _load_env() -> None:
    load_dotenv()


def build_chat_model() -> ChatDeepSeek:
    _load_env()
    return ChatDeepSeek(
        api_base="https://api.deepseek.com",
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        model="deepseek-chat",
        temperature=0.2,
    )


def build_reasoning_model() -> ChatDeepSeek:
    _load_env()
    return ChatDeepSeek(
        api_base="https://api.deepseek.com",
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        model="deepseek-reasoner",
    )


def build_llm() -> ChatDeepSeek:
    return build_chat_model()
