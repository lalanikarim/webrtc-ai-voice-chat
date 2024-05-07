from langchain_core.prompts.prompt import PromptTemplate
from langchain_community.chat_models import ChatOllama
from langchain_core.output_parsers import StrOutputParser


class Chain:
    def __init__(self, model="phi3"):
        self.prompt = PromptTemplate.from_template("""
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
        self.model = model
        self.chat_model = ChatOllama(model=self.model)

    def change_model(self, model: str):
        self.model = model
        self.chat_model = ChatOllama(model=self.model)

    def get_model(self):
        chain = self.prompt | self.chat_model | StrOutputParser()
        return chain
