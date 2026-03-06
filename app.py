from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser


# --- Configuration ---
CHROMA_DIR = "./chroma_db"
EMBEDDING_MODEL = "gemini-embedding-001"
LLM_MODEL = "llama-3.3-70b-versatile"


def main() -> None:
    """Run a simple console RAG app with RetrievalQA."""
    # Load environment variables from .env (expects GOOGLE_API_KEY)
    load_dotenv()

    # Recreate embeddings to load the existing ChromaDB store
    embeddings = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL)

    # Load the existing vector store from disk
    vectorstore = Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=embeddings,
    )

    # Configure Groq LLM (gratuit et ultra rapide)
    llm = ChatGroq(model=LLM_MODEL, temperature=0)

    # Create retriever
    retriever = vectorstore.as_retriever()
    
    # Create prompt template
    prompt = PromptTemplate(
        template="""Répondez à la question suivante basée uniquement sur le contexte fourni:

Contexte:
{context}

Question: {question}

Réponse:""",
        input_variables=["context", "question"]
    )
    
    # Create RAG chain with LCEL (LangChain Expression Language)
    qa_chain = (
        {"context": retriever | (lambda docs: "\n\n".join(doc.page_content for doc in docs)), "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    # Simple interactive loop
    print("Assistant RAG prêt. Tapez 'exit' pour quitter.")
    while True:
        question = input("\nVotre question: ").strip()
        if question.lower() in {"exit", "quit"}:
            print("Au revoir !")
            break
        if not question:
            print("Merci de poser une question.")
            continue

        try:
            answer = qa_chain.invoke(question)
            print(f"\nRéponse: {answer}")
        except Exception as e:
            error_msg = str(e)
            if "rate_limit" in error_msg.lower() or "429" in error_msg:
                print("\n⚠️  Limite de débit Groq atteinte. Attendez quelques secondes et réessayez.")
            else:
                print(f"\n❌ Erreur: {error_msg}")


if __name__ == "__main__":
    main()
