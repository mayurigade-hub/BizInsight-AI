import logging
from .config import RAGConfig

logger = logging.getLogger(__name__)

# We use a global variable to hold the embedding model instance so that we only load it once and reuse it across the application. 
_embedding_model = None

# The get_embedding_model function checks if the embedding model has already been loaded. If not, it initializes a new HuggingFaceEmbeddings instance with the specified model name and configuration from RAGConfig.  
def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        import os
        from langchain_huggingface import HuggingFaceEmbeddings
        local_model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models", "finetuned_complaint_model_final"))
        model_name = local_model_path if os.path.exists(local_model_path) else RAGConfig.EMBEDDING_MODEL
        logger.info(f"Loading embedding model: {model_name}")
        _embedding_model = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"device": "cpu"},  # Use CPU for embedding generation
            encode_kwargs={'normalize_embeddings': True} # Normalize embeddings for better similarity search performance
        )
    return _embedding_model