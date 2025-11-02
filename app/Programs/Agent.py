from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langchain_core.prompts.chat import(
    ChatPromptTemplate,
    MessagesPlaceholder,
    PromptTemplate
)
from enum import Enum
from app.config import OPENAI_API_KEY
from langchain.chains import ConversationalRetrievalChain

# 🔹 使用 LangChain ChatOpenAI
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=OPENAI_API_KEY)
# 🔹 Enum 定義
class QueryIntent(str, Enum):
    DETAIL = "detail"
    SIMILARITY = "similarity"
    FILTER = "filter"
    LIST = "list"
    DEFAULT = "default"
    
def get_llm():
    return llm

# 🔹 Intent 分類函式
async def classify_query_intent(question: str) -> QueryIntent:
    """
    使用 LLM 來判斷使用者的查詢意圖，回傳 Enum QueryIntent
    """
    # 🚀 乾淨的 system prompt
    system_prompt = f"""
        你是一個 Jira 查詢分類模型。
        問題：{question}
        你只能回覆以下其中一個單字（不得多字、不得附加說明）：

        {", ".join([e.value for e in QueryIntent if e != QueryIntent.DEFAULT])}, default

        定義如下：
        - detail：使用者想知道某個 Issue 的細節，例如「YTHG-830的內容」、「告訴我HR-12做了什麼」
        - similarity：使用者想找相似的案例，例如「有沒有類似YTHG-830的問題」
        - filter：使用者想根據條件或篩選找出相關項目，例如「找出薪資結算、離職的案例」、「comment有解決方法的問題」
        - list：使用者想列出全部相關項目，例如「列出所有行事曆相關的案例」
        若無法明確分類，請回答 default。
        請只輸出上面 Enum 的其中一個值（小寫）。
    """
    prompt = PromptTemplate.from_template(system_prompt)

    llmchain = LLMChain(llm=llm, prompt = prompt)
    # 🔹 呼叫模型
    response = await llmchain.ainvoke({"role": "user", "content": question})
    # 🔹 取出文字內容
    content = response['text']

    # 🔹 驗證是否為 Enum 成員
    return content

async def classify_issue(question:str):
    # 🚀 乾淨的 system prompt
    system_prompt = f"""
        你是一個 Jira 查詢分類模型。
        問題：{question}
        若問題中出現 Jira Issue Key（例如 YTHG-830、HR-12）
        請回答該Issue Key
        若無法明確分類，請回答None
        """
    prompt = PromptTemplate.from_template(system_prompt)

    llmchain = LLMChain(llm=llm, prompt = prompt)
    # 🔹 呼叫模型
    response = await llmchain.ainvoke({"role": "user", "content": question})
    # 🔹 取出文字內容
    content = response['text']
    return content
async def run_chain(Intent:QueryIntent,vectordb):
    qa_system_prompt = get_system_prompt()
    prompt = PromptTemplate(
        input_variables=["context", "question"],
        template=qa_system_prompt,
    )

    retriever = vectordb.as_retriever(search_type="similarity", search_kwargs={"k": 10})

    default_chain = ConversationalRetrievalChain.from_llm(
        llm,
        retriever, 
        combine_docs_chain_kwargs={"prompt": prompt},
        return_source_documents=True)
    
    result = await router_chain(question, default_chain)
    print(result)
    return result["answer"]

def get_system_prompt()-> str:
    prompt = """
        You are a Jira issue assistant. You have access to Jira issues with fields:
        key, summary, description, status.
        response answer in Traditional Chinese.
        Context:
        {context}

        Question:
        {question}
    """
    return prompt