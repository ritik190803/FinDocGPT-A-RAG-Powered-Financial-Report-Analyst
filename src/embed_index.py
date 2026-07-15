import os
import json
import chromadb
from sentence_transformers import SentenceTransformer

def build_vector_database():
    chunks_file = "data/processed_chunks.jsonl"
    db_dir = "data/chroma_db"
    collection_name = "financial_filings"
    
    if not os.path.exists(chunks_file):
        print(f"Error: {chunks_file} not found. Please run ingest.py first.")
        return

    # 1. Initialize the local embedding model
    print("Loading embedding model (sentence-transformers/all-MiniLM-L6-v2)...")
    # This model is lightweight, free, and runs entirely on your CPU local machine
    embed_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    
    # 2. Read all chunks from the JSONL file
    print("Reading chunks from disk...")
    chunks = []
    with open(chunks_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                chunks.append(json.loads(line))
                
    print(f"Loaded {len(chunks)} chunks to process.")
    
    # 3. Initialize Persistent ChromaDB Client
    # This saves the database into a local folder instead of running it in volatile memory
    chroma_client = chromadb.PersistentClient(path=db_dir)
    
    # Create or clear the collection
    print(f"Setting up ChromaDB collection: '{collection_name}'...")
    try:
        chroma_client.delete_collection(name=collection_name)
    except Exception:
        # Collection didn't exist yet, which is fine
        pass
        
    collection = chroma_client.create_collection(name=collection_name)
    
    # 4. Batch embed and insert into ChromaDB
    # Processing in batches prevents overloading memory space
    batch_size = 100
    print("Generating embeddings and indexing chunks into Vector DB...")
    
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        
        # Prepare arrays for ChromaDB ingestion
        documents = [c["chunk_text"] for c in batch]
        metadatas = [c["metadata"] for c in batch]
        # ChromaDB requires a string ID for every single record
        ids = [f"id_{idx}" for idx in range(i, i + len(batch))]
        
        # Calculate embeddings for the current text block batch
        embeddings = embed_model.encode(documents).tolist()
        
        # Upsert vectors + string text + metadata maps together
        collection.add(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        print(f"  Indexed chunks {i} to {min(i + batch_size, len(chunks))}...")
        
    print(f"\nVector Database Successfully Created! Persistent files saved to '{db_dir}'.")

if __name__ == "__main__":
    build_vector_database()