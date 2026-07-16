# src/rag_pipeline.py

import os
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"
import chromadb
from groq import Groq
# To this:
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from prompt_templates import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

# Load configuration parameters from .env file
load_dotenv(dotenv_path="fin_doc_api.env")

class FinancialRAGPipeline:
    def __init__(self):
        self.db_dir = "data/chroma_db"
        self.collection_name = "financial_filings"
        
        # Initialize local embedder
        self.embed_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        
        # Initialize Persistent Vector Database Connection
        self.chroma_client = chromadb.PersistentClient(path=self.db_dir)
        self.collection = self.chroma_client.get_collection(name=self.collection_name)
        
        # Initialize Groq Client
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("CRITICAL: GROQ_API_KEY is missing from your environment setup file.")
        self.groq_client = Groq(api_key=api_key)

    def retrieve_context(self, query_text, top_k=4):
        """Vector search to find top matching text snippets."""
        query_vector = self.embed_model.encode([query_text]).tolist()
        results = self.collection.query(query_embeddings=query_vector, n_results=top_k)
        
        formatted_chunks = []
        raw_documents = results['documents'][0]
        metadatas = results['metadatas'][0]
        
        for idx in range(len(raw_documents)):
            meta = metadatas[idx]
            chunk_info = f"--- Source Document: {meta['company']} | Year: {meta['fiscal_year']} | Page: {meta['page_number']} ---\n{raw_documents[idx]}"
            formatted_chunks.append(chunk_info)
            
        return "\n\n".join(formatted_chunks), results

    def query(self, user_question):
        """Main interface routing data from query text to local search to LLM delivery."""
        # 1. Fetch matching blocks
        context_str, raw_results = self.retrieve_context(user_question)
        
        # 2. Build explicit operational prompt boundaries
        user_content = USER_PROMPT_TEMPLATE.format(context_str=context_str, query_str=user_question)
        
        # 3. Request inferred completion via fast Groq endpoints
        # Using llama-3.3-70b-specdec or llama3-70b-8192 for high analytical reasoning depth
        print("Querying LLM via Groq Engine...")
        chat_completion = self.groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.0  # Kept strict at 0 to prioritize grounding over creative output
        )
        
        return {
            "answer": chat_completion.choices[0].message.content,
            "raw_metadata": raw_results['metadatas'][0]
        }

if __name__ == "__main__":
    pipeline = FinancialRAGPipeline()
    
    # Test execution
    test_query = "What specific risks does Apple face regarding global trade, tariffs, and manufacturing concentration?"
    response = pipeline.query(test_query)
    
    print("\n================= LLM RESPONSE =================")
    print(response["answer"])
    print("=================================================")