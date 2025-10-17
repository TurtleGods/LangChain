from langchain.chains import LLMChain
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts.chat import(
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
import os

def create_chain(input_language: str, output_language: str, text: str) -> str:
    OPENAI_API_KEY = os.getenv("GOOGLE_API_KEY")
    chat = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0,
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )

    template = (
        "You are a helpful assistant that translates {input_language} to {output_language}."
    )

    systemMessagePromptTemplate = SystemMessagePromptTemplate.from_template(template)

    human_template = "{text}"
    humanMessagePromptTemplate = HumanMessagePromptTemplate.from_template(human_template)

    chat_prompt = ChatPromptTemplate.from_messages([
        systemMessagePromptTemplate,
        humanMessagePromptTemplate
    ])

    chain = LLMChain(llm=chat,prompt=chat_prompt)

    result = chain.run(
        input_language=input_language,
        output_language=output_language,
        text=text
    )
    return result.strip()