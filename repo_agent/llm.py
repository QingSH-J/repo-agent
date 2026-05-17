from langchain_deepseek import ChatDeepSeek
from dotenv import load_dotenv
import os
def build_llm() -> ChatDeepSeek:
    load_dotenv()
    return ChatDeepSeek(
        api_base="https://api.deepseek.com",
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        model="deepseek-chat",
        temperature=0.2,
    )