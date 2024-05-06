from langchain_core.prompts.prompt import PromptTemplate
from langchain_community.chat_models import ChatOllama
from langchain_core.output_parsers import StrOutputParser

prompt = PromptTemplate.from_template("""
You are a helpful assistant. 
Respond truthfully to the best of your abilities. 
Only answer in short one or two sentences.
Do not answer with a question.

Human: {human_input}
AI: """)

chat_model = ChatOllama(model="phi3:latest")

chain = prompt | chat_model | StrOutputParser()
