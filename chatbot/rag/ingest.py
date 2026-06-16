import shutil
from pathlib import Path
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from .retriever import get_retriever
from .config import MANUALS_DIR, VECTORSTORE_DIR, DOCSTORE_PATH

# Approximate characters per page in a typical Word document.
_CHARS_PER_PAGE = 3000


def _load_docx_by_page(file_path: str) -> list[Document]:
    """Load a DOCX file as one Document per page.

    Strategy:
    1. Use python-docx to collect paragraphs and detect explicit page breaks.
    2. If explicit breaks are found, split there.
    3. Otherwise fall back to splitting by approximate character count
       (~3000 chars per page) so long documents still get sensible page numbers.
    """
    from docx import Document as DocxDoc
    from docx.oxml.ns import qn

    docx = DocxDoc(file_path)
    pages_text: list[str] = []
    current: list[str] = []

    for para in docx.paragraphs:
        # Detect explicit page-break runs inside this paragraph
        has_break = any(
            br.get(qn("w:type")) == "page"
            for run in para.runs
            for br in run._element.findall(f".//{qn('w:br')}")
        )
        if has_break and current:
            pages_text.append("\n".join(current))
            current = []

        if para.text.strip():
            current.append(para.text)

    if current:
        pages_text.append("\n".join(current))

    # Fallback: no explicit page breaks found → split by character count
    if len(pages_text) <= 1:
        full_text = pages_text[0] if pages_text else ""
        pages_text = [
            full_text[i : i + _CHARS_PER_PAGE]
            for i in range(0, max(len(full_text), 1), _CHARS_PER_PAGE)
        ]

    return [
        Document(
            page_content=text,
            metadata={"source": str(file_path), "page": page_num},
        )
        for page_num, text in enumerate(pages_text)
        if text.strip()
    ]


def load_documents() -> list[Document]:
    docs = []

    # PDFs — one Document per page (PyPDFLoader handles this natively)
    pdf_loader = DirectoryLoader(
        str(MANUALS_DIR),
        glob="**/*.pdf",
        loader_cls=PyPDFLoader,
        show_progress=True,
    )
    docs.extend(pdf_loader.load())

    # DOCX — custom page-aware loader
    for docx_path in Path(MANUALS_DIR).rglob("*.docx"):
        print(f"  Loading DOCX: {docx_path.name}")
        pages = _load_docx_by_page(str(docx_path))
        print(f"    → {len(pages)} pages detected")
        docs.extend(pages)

    return docs


def ingest():
    print("Loading documents from", MANUALS_DIR)
    docs = load_documents()
    print(f"  Loaded {len(docs)} pages.")

    print("Clearing existing vectorstore and docstore...")
    if VECTORSTORE_DIR.exists():
        shutil.rmtree(VECTORSTORE_DIR)
    if DOCSTORE_PATH.exists():
        DOCSTORE_PATH.unlink()

    print("Embedding child chunks and storing parent chunks...")
    retriever = get_retriever()
    retriever.add_documents(docs)
    print(f"  Done. Vectorstore → {VECTORSTORE_DIR}")
    print(f"  Done. Docstore    → {DOCSTORE_PATH}")
