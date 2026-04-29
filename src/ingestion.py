import os
import shutil
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma



def delete_chroma_db(project_root):
    db_path = os.path.join(project_root, "chroma_db")

    print("\nDeleting existing ChromaDB...")
    print("Path:", db_path)

    shutil.rmtree(db_path, ignore_errors=True)

    if not os.path.exists(db_path):
        print("ChromaDB deleted successfully\n")
    else:
        print("Failed to delete ChromaDB\n")

def load_all_pdfs(data_path):
    all_docs = []

    for file in os.listdir(data_path):
        if file.endswith(".pdf"):
            full_path = os.path.join(data_path, file)
            loader = PyPDFLoader(full_path)
            docs = loader.load()

            # Adding source metadata
            for doc in docs:
                doc.metadata["source"] = file

            all_docs.extend(docs)

    return all_docs

def chunk_documents(documents):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )

    chunks = text_splitter.split_documents(documents)

    # Adding chunk_id metadata
    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = i

    return chunks

def main():
    # Get project root dynamically
    current_dir = os.path.dirname(__file__)
    project_root = os.path.abspath(os.path.join(current_dir, "../"))

    delete_chroma_db(project_root)

    data_path = os.path.join(project_root, "data")

    print("Loading PDFs...")
    docs = load_all_pdfs(data_path)
    print(f"Total documents loaded: {len(docs)}")

    print("\nChunking documents...")
    chunks = chunk_documents(docs)
    print(f"Total chunks created: {len(chunks)}")

if __name__ == "__main__":
    main()