from typing import List
from langchain_core.embeddings import Embeddings


class LocalEmbeddings(Embeddings):
    """Local sentence-transformers embeddings — no API key required.

    Uses all-MiniLM-L6-v2 by default (22 MB, 384-dim, fast on CPU).
    Ideal for development when running alongside a cloud LLM like Gemini.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise ImportError("pip install sentence-transformers") from e

        self._model = SentenceTransformer(model_name)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._model.encode(texts, show_progress_bar=False).tolist()

    def embed_query(self, text: str) -> List[float]:
        return self._model.encode([text], show_progress_bar=False)[0].tolist()
