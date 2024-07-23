import os

from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

# TODO remove
SECRET_API_KEY = "sk-proj-DkDCIuko5FJRnUDPP8H4T3BlbkFJUmZotEBeaTE591lk7mZQ"
os.environ["OPENAI_API_KEY"] = SECRET_API_KEY
os.environ.get("OPENAI_API_KEY")
MODEL = "gpt-4o"
TEMPERATURE = 0
TOP_P = 1


class LLM:
    def __init__(self):
        self.llm = ChatOpenAI(
            openai_api_key=SECRET_API_KEY,
            model_name=MODEL,
            temperature=TEMPERATURE,
            top_p=TOP_P,
        )
        self.prompt = PromptTemplate(input_variables=["input_text"], template="{input_text}")

    def ask(self, input_text: str):
        if self.llm is None:
            raise Exception("ERROR: Large Language Model not initialized. Call __init__().")
        return self.llm.invoke(input_text)
