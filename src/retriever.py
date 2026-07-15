import chromadb
from sentence_transformers import SentenceTransformer

def test_retrieval(query_text, top_k=3):
    db_dir = "data/chroma_db"
    collection_name = "financial_filings"
    
    # 1. Load the exact same embedding model used during ingestion
    embed_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    
    # 2. Connect to the local persistent database
    chroma_client = chromadb.PersistentClient(path=db_dir)
    collection = chroma_client.get_collection(name=collection_name)
    
    # 3. Convert user query text into a vector
    print(f"\nSearching database for: '{query_text}'...")
    query_vector = embed_model.encode([query_text]).tolist()
    
    # 4. Perform vector similarity search
    results = collection.query(
        query_embeddings=query_vector,
        n_results=top_k
    )
    
    # 5. Output retrieved contexts to verify metadata alignment
    print("\n--- RETRIEVED CHUNKS ---")
    for idx in range(len(results['documents'][0])):
        text = results['documents'][0][idx]
        metadata = results['metadatas'][0][idx]
        
        print(f"\n[Match #{idx + 1}] Source: {metadata['company']} ({metadata['fiscal_year']}), Page: {metadata['page_number']}")
        # Print just the first 300 characters of the chunk to keep it readable
        print(f"Excerpt: {text[:300]}...")
        print("-" * 40)

if __name__ == "__main__":
    # Test with a question targeted at Apple's or Tesla's files
    sample_query = "What are the primary risk factors mentioned regarding supply chain or manufacturing operations?"
    test_retrieval(sample_query)