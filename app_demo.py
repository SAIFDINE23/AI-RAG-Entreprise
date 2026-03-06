from dotenv import load_dotenv

from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings


# --- Configuration ---
CHROMA_DIR = "./chroma_db"
EMBEDDING_MODEL = "gemini-embedding-001"


def main() -> None:
    """Demo app showing retrieval without LLM calls."""
    # Load environment variables from .env (expects GOOGLE_API_KEY)
    load_dotenv()

    # Recreate embeddings to load the existing ChromaDB store
    embeddings = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL)

    # Load the existing vector store from disk
    vectorstore = Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=embeddings,
    )

    # Create retriever
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})  # Get top 3 chunks

    # Simple interactive loop
    print("🚀 Assistant RAG - Mode DEMO (sans LLM)")
    print("Affiche les chunks similaires trouvés dans ChromaDB")
    print("Tapez 'exit' pour quitter.\n")
    
    while True:
        question = input("Votre question: ").strip()
        if question.lower() in {"exit", "quit"}:
            print("Au revoir !")
            break
        if not question:
            print("Merci de poser une question.")
            continue

        # Retrieve similar chunks WITHOUT calling LLM
        docs = retriever.invoke(question)
        
        print(f"\n📄 {len(docs)} chunks pertinents trouvés:\n")
        for i, doc in enumerate(docs, 1):
            print(f"--- Chunk {i} ---")
            print(doc.page_content[:500])  # Show first 500 chars
            if len(doc.page_content) > 500:
                print("... [texte tronqué]")
            print()


if __name__ == "__main__":
    main()
