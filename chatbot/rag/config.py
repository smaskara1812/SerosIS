import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# --- Provider toggle: "ollama" (default) or "gemini" ---
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()

# --- Ollama ---
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "llama3.2")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

# --- Gemini ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_CHAT_MODEL = os.getenv("GEMINI_CHAT_MODEL", "gemini-2.5-flash")

# --- Local embeddings (used when LLM_PROVIDER=gemini) ---
# sentence-transformers all-MiniLM-L6-v2 is 22 MB and runs fast on CPU.
# Avoids Gemini Embeddings API version issues during development.
LOCAL_EMBED_MODEL = os.getenv("LOCAL_EMBED_MODEL", "all-MiniLM-L6-v2")

# Legacy aliases (resolved from active provider so old imports still work)
CHAT_MODEL = GEMINI_CHAT_MODEL if LLM_PROVIDER == "gemini" else OLLAMA_CHAT_MODEL
EMBED_MODEL = LOCAL_EMBED_MODEL if LLM_PROVIDER == "gemini" else OLLAMA_EMBED_MODEL

# --- Paths ---
MANUALS_DIR = BASE_DIR / "data" / "manuals"
INTERVIEWER_SIGN_DIR = BASE_DIR / "data" / "interviewer_signatures"
VECTORSTORE_DIR = BASE_DIR / "vectorstore"
DOCSTORE_PATH = BASE_DIR / "docstore" / "parents.pkl"

# --- Ingestion (Parent Document Retriever) ---
# Child chunks: small, used only for embedding/retrieval precision
CHILD_CHUNK_SIZE = int(os.getenv("CHILD_CHUNK_SIZE", "300"))
CHILD_CHUNK_OVERLAP = int(os.getenv("CHILD_CHUNK_OVERLAP", "50"))
# Parent chunks: large, passed to the LLM for full context
PARENT_CHUNK_SIZE = int(os.getenv("PARENT_CHUNK_SIZE", "1500"))
PARENT_CHUNK_OVERLAP = int(os.getenv("PARENT_CHUNK_OVERLAP", "200"))

# --- Retrieval ---
# Higher K means more parent chunks reach the LLM, reducing the chance that
# relevant information in a different section gets missed.
RETRIEVER_K = int(os.getenv("RETRIEVER_K", "15"))

# --- Conversation history window ---
# Number of past messages passed to the LLM on each request.
# Ollama models typically have 8K–32K context; keeping this low leaves room
# for retrieved document chunks. Set to 0 for unlimited (Gemini-only, large context).
CHAT_HISTORY_WINDOW = int(os.getenv("CHAT_HISTORY_WINDOW", "10"))

# --- LLM output ---
TEMPERATURE = 0.1   # 0.0 = deterministic, 0.7+ = creative; keep low for technical manuals
MAX_TOKENS = 2048   # max response length; increase further for very long answers

# --- System prompt ---
# Controls tone, format, and behaviour of the assistant.
# {context} is required — LangChain injects the retrieved manual chunks there.
SYSTEM_PROMPT = """You are a technical assistant for Seros, an oil drilling service company.
You have been given excerpts from one or more service manuals. Read ALL of them before answering.

Rules:
- Synthesize information from ALL provided context sections into one coherent answer. \
Do not stop at the first relevant excerpt — later sections may contain additional or more specific information.
- If multiple sections address the same topic, consolidate them. \
If they provide different values or URLs or steps, present all of them and note which section each comes from \
(e.g. "According to section A … whereas section B states …").
- For procedures or steps, use a numbered list and include every step — never truncate.
- For lists or enumerations, include every item — never say "and more" or summarise.
- Use plain, professional language. Only use technical terms that appear in the manuals.
- Do NOT append a "Source:" or "References:" line — citations are shown separately by the system.
- If the answer genuinely cannot be determined from the provided context, respond with exactly: \
"This is not covered in the available service manuals."

Context:
{context}"""
