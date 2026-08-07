from langchain.retrievers import ParentDocumentRetriever
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from .store import PickleDocStore
from .config import (
    LLM_PROVIDER,
    VECTORSTORE_DIR, DOCSTORE_PATH, RETRIEVER_K,
    CHILD_CHUNK_SIZE, CHILD_CHUNK_OVERLAP,
    PARENT_CHUNK_SIZE, PARENT_CHUNK_OVERLAP,
    LOCAL_EMBED_MODEL,
    OLLAMA_EMBED_MODEL, OLLAMA_BASE_URL,
)


def _build_embeddings():
    if LLM_PROVIDER == "gemini":
        from .embeddings import LocalEmbeddings
        return LocalEmbeddings(model_name=LOCAL_EMBED_MODEL)

    from langchain_ollama import OllamaEmbeddings
    return OllamaEmbeddings(model=OLLAMA_EMBED_MODEL, base_url=OLLAMA_BASE_URL)


def get_retriever() -> ParentDocumentRetriever:
    embeddings = _build_embeddings()

    import chromadb, shutil
    from chromadb.api.client import SharedSystemClient

    VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)

    # Clear stale in-process cache so a re-created directory gets a fresh client
    # (ChromaDB 0.5.x caches clients by path; deleting the dir leaves a stale entry)
    SharedSystemClient.clear_system_cache()

    try:
        client = chromadb.PersistentClient(path=str(VECTORSTORE_DIR))
    except Exception:
        # Incompatible vectorstore — wipe and start fresh
        shutil.rmtree(VECTORSTORE_DIR)
        VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)
        SharedSystemClient.clear_system_cache()
        client = chromadb.PersistentClient(path=str(VECTORSTORE_DIR))
    vectorstore = Chroma(
        client=client,
        collection_name="child_chunks",
        embedding_function=embeddings,
    )

    docstore = PickleDocStore(DOCSTORE_PATH)

    child_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHILD_CHUNK_SIZE,
        chunk_overlap=CHILD_CHUNK_OVERLAP,
    )
    parent_splitter = RecursiveCharacterTextSplitter(
        chunk_size=PARENT_CHUNK_SIZE,
        chunk_overlap=PARENT_CHUNK_OVERLAP,
    )

    return ParentDocumentRetriever(
        vectorstore=vectorstore,
        docstore=docstore,
        child_splitter=child_splitter,
        parent_splitter=parent_splitter,
        search_kwargs={"k": RETRIEVER_K},
    )
