import os
from dotenv import load_dotenv

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma


# --- Configuration ---
PDF_PATH = "doc.pdf"
CHROMA_DIR = "./chroma_db"
EMBEDDING_MODEL = "gemini-embedding-001"


def main() -> None:
    """Ingest a local PDF into a persistent ChromaDB vector store."""
    # Load environment variables from .env (expects GOOGLE_API_KEY)
    load_dotenv()

    # Basic existence check for the PDF file
    if not os.path.exists(PDF_PATH):
        raise FileNotFoundError(
            f"Le fichier '{PDF_PATH}' est introuvable à la racine du projet."
        )

    # Load the PDF into LangChain documents
    loader = PyPDFLoader(PDF_PATH)
    documents = loader.load()

    # Split documents into smaller chunks for better retrieval
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
    )
    chunks = splitter.split_documents(documents)

    # Initialize Google Gemini embeddings
    embeddings = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL)

    # Create (or overwrite) the persistent ChromaDB vector store
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_DIR,
    )

    print(f"Ingestion terminée. {len(chunks)} chunks vectorisés et persistés dans {CHROMA_DIR}.")


if __name__ == "__main__":
    main()
