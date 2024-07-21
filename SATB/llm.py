import os

from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

SECRET_API_KEY = "sk-XXXX"
os.environ["OPENAI_API_KEY"] = SECRET_API_KEY
os.environ.get("OPENAI_API_KEY")
MODEL = "gpt-4-turbo"
TEMPERATURE = 0
TOP_P = 1


class LLM:
    def __init__(self):
        self.llm = ChatOpenAI(
            openai_api_key=SECRET_API_KEY,
            model_name=MODEL,
            temperature=TEMPERATURE,
            model_kwargs={
                "top_p": TOP_P,
            }
        )
        self.prompt = PromptTemplate(input_variables=["input_text"], template="{input_text}")
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt)

    def ask(self, input_text: str):
        if self.llm is None:
            raise Exception("ERROR: Large Language Model not initialized. Call __init__().")
        return self.llm.invoke(input_text)
