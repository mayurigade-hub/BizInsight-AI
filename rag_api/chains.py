import logging
from langchain_classic.chains import RetrievalQA, ConversationalRetrievalChain
from langchain_classic.memory import ConversationBufferWindowMemory
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_classic.retrievers.multi_query import MultiQueryRetriever
import time
import threading
from langchain_classic.retrievers import ContextualCompressionRetriever
from langchain_classic.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder

from .vector_store import VectorStoreManager
from .config import RAGConfig

logger = logging.getLogger(__name__)
logging.getLogger("langchain.retrievers.multi_query").setLevel(logging.INFO)

custom_prompt_template = """You are a senior Business Intelligence & Customer Support consultant analyzing customer feedback.

Customer Context / Reviews:
{context}

User's Question:
{question}

Instructions:
1. Base your answer STRICTLY on the Customer Context provided above.
2. Directly answer the user's question in a professional, helpful tone.
3. DO NOT repeat the raw customer reviews in your answer. Just summarize the findings.
4. CRITICAL: If the Customer Context is empty, or does not contain the answer, you must output EXACTLY this sentence and nothing else: "The customer reviews do not mention this information."
"""

CUSTOM_PROMPT = PromptTemplate(
    template=custom_prompt_template,
    input_variables=["context", "question"]
)


class RAGChainManager:
    def __init__(self):
        self.vector_store_manager = VectorStoreManager()

        self.llm = ChatOpenAI(
            openai_api_key=RAGConfig.OPENROUTER_API_KEY,
            openai_api_base=RAGConfig.LLM_BASE_URL,
            model_name=RAGConfig.LLM_MODEL,
            temperature=RAGConfig.LLM_TEMPERATURE,
            max_tokens=RAGConfig.LLM_MAX_TOKENS,
            max_retries=4
        )

        self._qa_chain = None
        self._conv_chains = {}
        self._chain_last_access = {}
        self._session_timeout = 30 * 60
        self._lock = threading.Lock()

        logger.info("Loading Re-Ranker Model...")
        self.reranker_model = HuggingFaceCrossEncoder(model_name="cross-encoder/ms-marco-MiniLM-L-6-v2")
        self.compressor = CrossEncoderReranker(model=self.reranker_model, top_n=8)

    def get_qa_chain(self, search_filter=None):
        base_retriever = self.vector_store_manager.get_retriever(search_filter=search_filter)

        mq_retriever = MultiQueryRetriever.from_llm(retriever=base_retriever, llm=self.llm)

        compression_retriever = ContextualCompressionRetriever(
            base_compressor=self.compressor,
            base_retriever=mq_retriever
        )

        return RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=compression_retriever,
            return_source_documents=True,
            chain_type_kwargs={"prompt": CUSTOM_PROMPT},
            verbose=False
        )

    def get_conversational_chain(self, session_id: str, search_filter=None):
        chain_key = f"{session_id}_{str(search_filter)}"
        self._cleanup_expired_chains()

        if chain_key not in self._conv_chains:
            memory = ConversationBufferWindowMemory(
                memory_key="chat_history",
                return_messages=True,
                output_key="answer",
                k=RAGConfig.CONVERSATION_MEMORY_WINDOW
            )

            try:
                from database import load_chat_history
                past_turns = load_chat_history(
                    session_id, window=RAGConfig.CONVERSATION_MEMORY_WINDOW
                )
                for turn in past_turns:
                    if turn["role"] == "human":
                        memory.chat_memory.add_user_message(turn["content"])
                    elif turn["role"] == "ai":
                        memory.chat_memory.add_ai_message(turn["content"])
            except Exception as exc:
                logger.warning("Could not load persisted chat history for %s: %s", session_id, exc)

            base_retriever = self.vector_store_manager.get_retriever(search_filter=search_filter)

            mq_retriever = MultiQueryRetriever.from_llm(retriever=base_retriever, llm=self.llm)

            compression_retriever = ContextualCompressionRetriever(
                base_compressor=self.compressor,
                base_retriever=mq_retriever
            )

            chain = ConversationalRetrievalChain.from_llm(
                llm=self.llm,
                retriever=compression_retriever,
                memory=memory,
                return_source_documents=True,
                combine_docs_chain_kwargs={"prompt": CUSTOM_PROMPT},
                verbose=False
            )
            self._conv_chains[chain_key] = chain

        with self._lock:
            self._chain_last_access[chain_key] = time.time()
            return self._conv_chains[chain_key]

    def _cleanup_expired_chains(self):
        now = time.time()

        expired = [
            key
            for key, last_access in self._chain_last_access.items()
            if now - last_access > self._session_timeout
        ]

        with self._lock:
            for key in expired:
                self._conv_chains.pop(key, None)
                self._chain_last_access.pop(key, None)