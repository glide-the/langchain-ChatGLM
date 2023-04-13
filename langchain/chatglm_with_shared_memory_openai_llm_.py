from langchain.agents import ZeroShotAgent, Tool, AgentExecutor
from langchain.memory import ConversationBufferMemory, ReadOnlySharedMemory
from langchain import  LLMChain, PromptTemplate
from langchain.utilities import GoogleSearchAPIWrapper
from langchain.vectorstores import Chroma
from langchain.text_splitter import CharacterTextSplitter
 
 
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.embeddings.huggingface import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
from langchain.document_loaders import UnstructuredFileLoader
from chatglm_llm import ChatGLM
import sentence_transformers
import torch
import os
import readline
from langchain.llms import OpenAI 

from langchain.document_loaders import TextLoader


# Global Parameters
EMBEDDING_MODEL = "text2vec"
VECTOR_SEARCH_TOP_K = 6
LLM_MODEL = "chatglm-6b"
LLM_HISTORY_LEN = 10
DEVICE = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"

# Show reply with source text from input document
REPLY_WITH_SOURCE = True

embedding_model_dict = {
    "ernie-tiny": "nghuyong/ernie-3.0-nano-zh",
    "ernie-base": "nghuyong/ernie-3.0-base-zh",
    "text2vec": "GanymedeNil/text2vec-large-chinese",
}

llm_model_dict = {
    "chatglm-6b-int4-qe": "THUDM/chatglm-6b-int4-qe",
    "chatglm-6b-int4": "THUDM/chatglm-6b-int4",
    "chatglm-6b": "THUDM/chatglm-6b",
}


def init_cfg(LLM_MODEL, EMBEDDING_MODEL, LLM_HISTORY_LEN, V_SEARCH_TOP_K=6):
    global chatglm, embeddings, VECTOR_SEARCH_TOP_K
    VECTOR_SEARCH_TOP_K = V_SEARCH_TOP_K

    chatglm = ChatGLM()
    chatglm.load_model(model_name_or_path=llm_model_dict[LLM_MODEL])
    chatglm.history_len = LLM_HISTORY_LEN

    embeddings = HuggingFaceEmbeddings(model_name=embedding_model_dict[EMBEDDING_MODEL],)
    embeddings.client = sentence_transformers.SentenceTransformer(embeddings.model_name,
                                                                  device=DEVICE)

 

def init_docsearch():
    global chatglm,embeddings,state_of_search
    from pathlib import Path
    relevant_parts = []
    for p in Path(".").absolute().parts:
        relevant_parts.append(p)

    doc_path = str(Path(*relevant_parts) / "statefile/state_of_the_search.txt")
    loader = TextLoader(doc_path)
    documents = loader.load()
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    texts = text_splitter.split_documents(documents)
    docsearch = Chroma.from_documents(texts, embeddings, collection_name="state-of-search")
    state_of_search = RetrievalQA.from_chain_type(llm=chatglm, chain_type="stuff", retriever=docsearch.as_retriever())
 
def init_state_of_history():
    global chatglm,embeddings,state_of_history
    from pathlib import Path
    relevant_parts = []
    for p in Path(".").absolute().parts:
        relevant_parts.append(p)

    doc_path = str(Path(*relevant_parts) / "statefile/state_of_the_history.txt")
    loader = TextLoader(doc_path)
    documents = loader.load()
    text_splitter = CharacterTextSplitter(chunk_size=100, chunk_overlap=0)
    texts = text_splitter.split_documents(documents)
    docsearch = Chroma.from_documents(texts, embeddings, collection_name="state-of-history")
    state_of_history = RetrievalQA.from_chain_type(llm=chatglm, chain_type="stuff", retriever=docsearch.as_retriever())
 

def agents_answer():
    global chatglm
   
    template = """This is a conversation between a human and a bot:

    {chat_history}

    Write a summary of the conversation for {input}:
    """

    prompt = PromptTemplate(
        input_variables=["input", "chat_history"], 
        template=template
    )
    memory = ConversationBufferMemory(memory_key="chat_history")
    readonlymemory = ReadOnlySharedMemory(memory=memory)
    summry_chain = LLMChain(
        llm=chatglm, 
        prompt=prompt, 
        verbose=True, 
        memory=readonlymemory, # use the read-only memory to prevent the tool from modifying the memory
    )
    return summry_chain,memory


if __name__ == "__main__":
    global chatglm,state_of_search,state_of_history
    init_cfg(LLM_MODEL, EMBEDDING_MODEL, LLM_HISTORY_LEN)
    init_docsearch()
    init_state_of_history()

    summry_chain,memory = agents_answer()
    tools = [
        Tool(
            name = "State of Search QA System",
            func=state_of_search.run,
            description="当您需要搜索有关问题时非常有用。输入应该是一个完整的问题。"
        ),
        Tool(
            name = "state-of-history-qa",
            func=state_of_history.run,
            description="跟露露的历史对话 - 当提出我们之间发生了什么事请时，这里面的回答是很有用的"
        ),
        Tool(
            name = "Summary",
            func=summry_chain.run,
            description="useful for when you summarize a conversation. The input to this tool should be a string, representing who will read this summary."
        )
    ]

    prefix = """你需要充当一个倾听者,尽量回答人类的问题,你可以使用这里工具,它们非常有用:"""
    suffix = """Begin!"

    {chat_history}
    Question: {input}
    {agent_scratchpad}"""

    prompt = ZeroShotAgent.create_prompt(
        tools, 
        prefix=prefix, 
        suffix=suffix, 
        input_variables=["input", "chat_history", "agent_scratchpad"]
    )

    # 不能加载两个模型解析
    # llm_chatglm = ChatGLM()
    # llm_chatglm.load_model(model_name_or_path=llm_model_dict[LLM_MODEL])
    # llm_chatglm.history_len = LLM_HISTORY_LEN
    ## 使用openAI的
    llm_chain = LLMChain(llm=OpenAI(temperature=0), prompt=prompt)
    agent = ZeroShotAgent(llm_chain=llm_chain, tools=tools, verbose=True)
    agent_chain = AgentExecutor.from_agent_and_tools(agent=agent, tools=tools, verbose=True, memory=memory)


    # agent_chain.run(input="什么是 ChatGPT?")

    # agent_chain.run(input="谁开发了它?")
    agent_chain.run(input="我跟露露聊了什么?")
    agent_chain.run(input="她开心吗?")
    agent_chain.run(input="她有表达意见吗?")
    agent_chain.run(input="根据历史对话总结下?")
    agent_chain.run(input="""可以拓展下吗?，比如写个小作文。
    大纲：游戏的美好回忆，触不可及的距离，不在乎得失
    主题：露露的陪伴无比珍贵
    背景：游戏，通话，当下
    开篇需要以游戏相识你挑逗的话语讲起
    """)
    
