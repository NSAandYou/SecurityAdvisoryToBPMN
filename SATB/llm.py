from langchain_openai import ChatOpenAI


SECRET_API_KEY = "sk-proj-WESeYqSCKmS05ykqIZHST3BlbkFJ817JuF39HAUyELOBpXXb"


class LLM:
    def __init__(self):
        self.llm = ChatOpenAI(openai_api_key=SECRET_API_KEY, model_name="gpt-3.5-turbo")

    def ask(self, input_text: str):
        if self.llm is None:
            raise Exception("ERROR: Large Language Model not initialized. Call __init__().")
        return self.llm.invoke(input_text)
