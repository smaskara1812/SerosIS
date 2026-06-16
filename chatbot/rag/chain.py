from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_history_aware_retriever
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from .retriever import get_retriever
from .config import (
    LLM_PROVIDER,
    OLLAMA_CHAT_MODEL, OLLAMA_BASE_URL,
    GEMINI_API_KEY, GEMINI_CHAT_MODEL,
    TEMPERATURE, MAX_TOKENS, SYSTEM_PROMPT,
)

# Rewrites the user's follow-up question into a self-contained question
# using the conversation history, so retrieval works on vague references.
_CONTEXTUALIZE_PROMPT = """Given the conversation history and the latest user question, \
rewrite the question as a fully standalone question that can be understood without the history. \
Do NOT answer the question — only rephrase it if needed, otherwise return it as-is."""


def _build_llm():
    if LLM_PROVIDER == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=GEMINI_CHAT_MODEL,
            google_api_key=GEMINI_API_KEY,
            temperature=TEMPERATURE,
            max_output_tokens=MAX_TOKENS,
        )

    from langchain_ollama import ChatOllama
    return ChatOllama(
        model=OLLAMA_CHAT_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=TEMPERATURE,
        num_predict=MAX_TOKENS,
    )


def get_rag_chain():
    llm = _build_llm()
    retriever = get_retriever()

    # Step 1: rewrite the question to be standalone given the history
    contextualize_prompt = ChatPromptTemplate.from_messages([
        ("system", _CONTEXTUALIZE_PROMPT),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])
    history_aware_retriever = create_history_aware_retriever(llm, retriever, contextualize_prompt)

    # Step 2: answer using the retrieved context + history
    qa_prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])
    qa_chain = create_stuff_documents_chain(llm, qa_prompt)

    # chain.invoke({"input": "...", "chat_history": [HumanMessage(...), AIMessage(...), ...]})
    return create_retrieval_chain(history_aware_retriever, qa_chain)
