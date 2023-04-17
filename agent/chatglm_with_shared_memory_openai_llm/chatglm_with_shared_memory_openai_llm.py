import torch
from langchain.agents import ZeroShotAgent, Tool, AgentExecutor
from langchain.llms import OpenAI
from langchain.llms import LlamaCpp
from langchain import PromptTemplate, LLMChain
from langchain.memory import ConversationBufferMemory, ReadOnlySharedMemory
from langchain.chains import LLMChain, RetrievalQA
from langchain.embeddings.huggingface import HuggingFaceEmbeddings
from langchain.prompts import PromptTemplate
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.document_loaders import TextLoader

from agent.document_loaders import Dialogue, parse_dialogue, DialogueLoader
from models import ChatGLM
import sentence_transformers
from configs.model_config import *


class ChatglmWithSharedMemoryOpenaiLLM:

    def __init__(self, params: dict = None):
        params = params or {}
        self.embedding_model = params.get('embedding_model', 'text2vec')
        self.vector_search_top_k = params.get('vector_search_top_k', 6)
        self.llm_model = params.get('llm_model', 'chatglm-6b')
        self.llm_history_len = params.get('llm_history_len', 10)
        self.dialogue_path = params.get('dialogue_path', '')
        self.device = 'cuda' if params.get('use_cuda', False) else 'cpu'

        self._load_scenario_dia()
        self._init_cfg()
        self._init_state_of_history()
        self.summry_chain, self.memory = self._agents_answer()
        self.agent_chain = self._create_agent_chain()

    def _load_scenario_dia(self):
        # 对话场景
        self.dialogue = parse_dialogue(self.dialogue_path)

    def _init_cfg(self):
        self.chatglm = ChatGLM()
        self.chatglm.load_model(model_name_or_path=llm_model_dict[self.llm_model])
        self.chatglm.history_len = self.llm_history_len
        self.embeddings = HuggingFaceEmbeddings(model_name=embedding_model_dict[self.embedding_model], )
        self.embeddings.client = sentence_transformers.SentenceTransformer(self.embeddings.model_name,
                                                                           device=self.device)

    def _init_state_of_history(self):
        loader = DialogueLoader(self.dialogue)
        documents = loader.load()
        text_splitter = CharacterTextSplitter(chunk_size=3, chunk_overlap=1)
        texts = text_splitter.split_documents(documents)
        docsearch = Chroma.from_documents(texts, self.embeddings, collection_name="state-of-history")
        self.state_of_history = RetrievalQA.from_chain_type(llm=self.chatglm, chain_type="stuff",
                                                            retriever=docsearch.as_retriever())

    def _agents_answer(self):
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
            llm=self.chatglm,
            prompt=prompt,
            verbose=True,
            memory=readonlymemory,  # use the read-only memory to prevent the tool from modifying the memory
        )
        return summry_chain, memory

    def _create_agent_chain(self):
        dialogue_participants = self.dialogue.participants_to_export()
        tools = [
            Tool(
                name="State of Dialogue History System",
                func=self.state_of_history.run,
                description=f"{dialogue_participants}"
            ),
            Tool(
                name="Summary",
                func=self.summry_chain.run,
                description="useful for when you summarize a conversation. The input to this tool should be a string, representing who will read this summary."
            )
        ]

        prefix = """Have a conversation with a human, answering the following questions as best you can. You have access to the following tools:"""
        suffix = """Begin!

        {chat_history}
        Question: {input}
        {agent_scratchpad}"""

        prompt = ZeroShotAgent.create_prompt(
            tools,
            prefix=prefix,
            suffix=suffix,
            input_variables=["input", "chat_history", "agent_scratchpad"]
        )
        # llm = LlamaCpp(model_path="/media/gpt4-pdf-chatbot-langchain/llama.cpp/zh-models/7B/ggml-model-q4_0.bin")
        # llm_chain = LLMChain(llm=llm, prompt=prompt)
        llm_chain = LLMChain(llm=OpenAI(temperature=0), prompt=prompt)
        agent = ZeroShotAgent(llm_chain=llm_chain, tools=tools, verbose=True)
        agent_chain = AgentExecutor.from_agent_and_tools(agent=agent, tools=tools, verbose=True, memory=self.memory)

        return agent_chain
