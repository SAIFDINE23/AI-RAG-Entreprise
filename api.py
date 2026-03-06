import os
import shutil
import logging
import traceback
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- Configuration ---
CHROMA_DIR = "./chroma_db"
UPLOAD_DIR = "./uploads"
EMBEDDING_MODEL = "gemini-embedding-001"
LLM_MODEL = "llama-3.3-70b-versatile"

# --- Global state ---
qa_chain = None
doc_info = {"filename": None, "pages": 0, "chunks": 0, "ready": False}


def build_chain(vectorstore):
    """Build the RAG chain from a vector store."""
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
    llm = ChatGroq(model=LLM_MODEL, temperature=0)

    prompt = PromptTemplate(
        template="""Tu es un assistant expert en analyse de documents. Réponds à la question en te basant UNIQUEMENT sur le contexte fourni.
Si le contexte ne contient pas assez d'informations, dis-le clairement.
Réponds de manière structurée et précise.

Contexte:
{context}

Question: {question}

Réponse:""",
        input_variables=["context", "question"],
    )

    return (
        {
            "context": retriever | (lambda docs: "\n\n".join(d.page_content for d in docs)),
            "question": RunnablePassthrough(),
        }
        | prompt
        | llm
        | StrOutputParser()
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: load existing DB if present."""
    global qa_chain, doc_info
    load_dotenv()
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # If a ChromaDB already exists, load it
    if os.path.exists(CHROMA_DIR) and os.listdir(CHROMA_DIR):
        try:
            embeddings = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL)
            vectorstore = Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)
            count = vectorstore._collection.count()
            if count > 0:
                qa_chain = build_chain(vectorstore)
                doc_info = {"filename": "Document précédent", "pages": 0, "chunks": count, "ready": True}
                print(f"✅ Base existante chargée ({count} chunks)")
        except Exception:
            pass

    print("🚀 Serveur prêt.")
    yield


app = FastAPI(title="Enterprise RAG Assistant", lifespan=lifespan)


# --- Models ---
class Question(BaseModel):
    question: str


class Answer(BaseModel):
    answer: str


class DocStatus(BaseModel):
    filename: str | None
    pages: int
    chunks: int
    ready: bool


# --- Routes ---
@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.get("/api/status", response_model=DocStatus)
async def status():
    """Return current document status."""
    return DocStatus(**doc_info)


@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload a PDF, ingest it into ChromaDB, and build the RAG chain."""
    global qa_chain, doc_info

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Seuls les fichiers PDF sont acceptés.")

    filepath = os.path.join(UPLOAD_DIR, file.filename)
    try:
        content = await file.read()
        with open(filepath, "wb") as f:
            f.write(content)
        logger.info(f"PDF sauvegardé: {filepath}")
    except Exception as e:
        logger.error(f"Erreur sauvegarde: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Erreur sauvegarde fichier: {e}")

    try:
        loader = PyPDFLoader(filepath)
        documents = loader.load()
        num_pages = len(documents)
        logger.info(f"PDF chargé: {num_pages} pages")

        if num_pages == 0:
            raise HTTPException(status_code=400, detail="Le PDF est vide ou illisible.")

        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = splitter.split_documents(documents)
        logger.info(f"Split: {len(chunks)} chunks")

        # Release old chain before deleting DB
        qa_chain = None

        # Use ChromaDB client API to reset cleanly (avoid file lock issues)
        import chromadb
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        for col in client.list_collections():
            client.delete_collection(col.name)
        del client

        embeddings = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL)
        vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=CHROMA_DIR,
        )
        logger.info(f"VectorStore créé: {vectorstore._collection.count()} chunks")

        qa_chain = build_chain(vectorstore)
        logger.info("RAG chain construite")

        doc_info = {
            "filename": file.filename,
            "pages": num_pages,
            "chunks": len(chunks),
            "ready": True,
        }

        return {
            "message": f"'{file.filename}' analysé avec succès",
            "pages": num_pages,
            "chunks": len(chunks),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur upload: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'analyse : {str(e)}")


@app.post("/api/ask", response_model=Answer)
async def ask(payload: Question):
    """Answer a question using the RAG chain."""
    if qa_chain is None:
        raise HTTPException(status_code=400, detail="Aucun document chargé. Veuillez d'abord uploader un PDF.")

    try:
        answer = qa_chain.invoke(payload.question)
        return Answer(answer=answer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Serve static files — MUST be after all API routes
app.mount("/static", StaticFiles(directory="static"), name="static")
