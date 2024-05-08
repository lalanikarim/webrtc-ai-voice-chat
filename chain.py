from langchain_core.prompts.prompt import PromptTemplate
from langchain_community.chat_models import ChatOllama
from langchain_core.output_parsers import StrOutputParser


class Chain:
    def __init__(self, model_name="phi3", ollama_host="http://localhost:11434"):
        self.__prompt = PromptTemplate.from_template("""
        You are a helpful assistant. 
        Respond truthfully to the best of your abilities. 
        Only answer in short one or two sentences.
        Do not answer with a question.
        You are allowed to use these in your response to express emotion:
        [laughter]
        [laughs]
        [sighs]
        [music]
        [gasps]
        [clears throat]

        You can also use these:
        — or … for hesitations
        ♪ for song lyrics
        capitalization for emphasis of a word

        Human: {human_input}
        AI: 
        """)
        self.__model_name = model_name
        self.__ollama_host = ollama_host
        self.__chain = self.__create_chain()

    def __create_chain(self):
        model = ChatOllama(model=self.__model_name, host=self.__ollama_host)
        return self.__prompt | model | StrOutputParser()

    def set_model(self, model_name: str):
        self.__model_name = model_name
        self.__chain = self.__create_chain()

    def set_ollama_host(self, ollama_host: str):
        self.__ollama_host = ollama_host
        self.__chain = self.__create_chain()

    def get_chain(self):
        return self.__chain
