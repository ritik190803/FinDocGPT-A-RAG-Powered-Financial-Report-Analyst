import os
import time
import json
from typing import List

os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"

import chromadb
from groq import Groq
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from prompt_templates import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

# Load environment variables
load_dotenv(dotenv_path="fin_doc_api.env")


class FinancialRAGPipeline:

    def __init__(self):
        self.db_dir = "data/chroma_db"
        self.collection_name = "financial_filings"

        print("Loading embedding model...")
        self.embed_model = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2"
        )

        print("Connecting to ChromaDB...")
        self.chroma_client = chromadb.PersistentClient(path=self.db_dir)
        self.collection = self.chroma_client.get_collection(
            name=self.collection_name
        )

        print("Initializing Groq Client...")
        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables.")

        self.groq_client = Groq(api_key=api_key)
        print("RAG Pipeline Initialized Successfully.\n")

    # -------------------------------------------------------------------------
    # STEP 1: Agentic Sub-Query Decomposition (LLM Router)
    # -------------------------------------------------------------------------
    def decompose_query(self, user_query: str) -> List[str]:
        """
        Uses LLM reasoning to decompose a complex prompt into focused search queries.
        Returns a list of clean sub-queries to execute against ChromaDB.
        """
        router_prompt = f"""
You are an expert search query planner for a Financial RAG system.
Analyze the following user prompt and break it down into 1 to 5 distinct, highly targeted search sub-queries to query vector embeddings of SEC 10-K filings.

If the prompt asks about multiple companies or topics, generate one focused sub-query for EACH company/topic.
If the prompt is simple or targets a single entity, return just 1 query.

Return ONLY a raw JSON array of strings, exactly like this:
["sub query 1", "sub query 2"]

User Prompt: "{user_query}"
        """

        try:
            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": router_prompt}],
                temperature=0.0
            )
            raw_content = response.choices[0].message.content.strip()
            
            # Clean possible markdown backticks from LLM output
            if raw_content.startswith("```"):
                raw_content = raw_content.split("```")[1]
                if raw_content.lower().startswith("json"):
                    raw_content = raw_content[4:]
            
            sub_queries = json.loads(raw_content)
            if isinstance(sub_queries, list) and len(sub_queries) > 0:
                return sub_queries
        except Exception as e:
            print(f"Query decomposition fallback triggered due to parsing error: {e}")

        # Fallback to the raw query if parsing fails
        return [user_query]

    # -------------------------------------------------------------------------
    # STEP 2: Parallel Search & Context Fusion
    # -------------------------------------------------------------------------
    def retrieve_context(self, user_query: str, top_k_per_query: int = 3):
        """
        Executes vector search across all generated sub-queries and fuses/deduplicates 
        the retrieved contexts.
        """
        print("=" * 70)
        print("STEP 1 : Agentic Sub-Query Generation")
        sub_queries = self.decompose_query(user_query)
        print(f"Generated {len(sub_queries)} Targeted Sub-Queries:")
        for idx, sq in enumerate(sub_queries, 1):
            print(f"  [{idx}] {sq}")

        start_time = time.time()

        all_documents = []
        all_metadatas = []
        seen_chunks = set()

        # Execute vector search for each sub-query
        for sq in sub_queries:
            query_vector = self.embed_model.encode([sq]).tolist()
            results = self.collection.query(
                query_embeddings=query_vector,
                n_results=top_k_per_query
            )

            docs = results["documents"][0]
            metas = results["metadatas"][0]

            for d, m in zip(docs, metas):
                # Create a unique identifier to avoid duplicate chunks in the prompt
                chunk_id = f"{m.get('company')}_{m.get('fiscal_year')}_{m.get('page_number')}_{d[:30]}"
                if chunk_id not in seen_chunks:
                    seen_chunks.add(chunk_id)
                    all_documents.append(d)
                    all_metadatas.append(m)

        end_time = time.time()
        print(f"\nVector Search Completed in {end_time - start_time:.2f} seconds")
        print(f"Total Unique Chunks Assembled: {len(all_documents)}\n")

        formatted_chunks = []
        for idx, (doc, meta) in enumerate(zip(all_documents, all_metadatas), 1):
            print(f"Chunk {idx:02d} -> {meta['company']} | FY{meta['fiscal_year']} | Page {meta['page_number']}")
            formatted_chunks.append(
                f"--- Source Document: {meta['company']} | Year: {meta['fiscal_year']} | Page: {meta['page_number']} ---\n{doc}"
            )

        print("=" * 70)

        raw_results_format = {"metadatas": [all_metadatas]}
        return "\n\n".join(formatted_chunks), raw_results_format

    # -------------------------------------------------------------------------
    # STEP 3: Final Generation
    # -------------------------------------------------------------------------
    def query(self, user_question: str):
        print("\n" + "#" * 80)
        print("NEW QUERY RECEIVED")
        print("#" * 80)

        # Retrieve and merge context dynamically
        context_str, raw_results = self.retrieve_context(user_question)

        print("\nSTEP 2 : Creating Prompt")
        user_content = USER_PROMPT_TEMPLATE.format(
            context_str=context_str,
            query_str=user_question
        )

        print(f"Prompt Size : {len(user_content)} characters")
        print("\nSTEP 3 : Sending request to Groq LLM...")

        start_time = time.time()

        try:
            chat_completion = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.0
            )

            end_time = time.time()
            print(f"Groq Response Received in {end_time - start_time:.2f} seconds")

            answer = chat_completion.choices[0].message.content

            print("\nSTEP 4 : Answer Generated Successfully")
            print("Answer Length :", len(answer))
            print("=" * 80)

            return {
                "answer": answer,
                "raw_metadata": raw_results["metadatas"][0]
            }

        except Exception as e:
            print("\n" + "=" * 80)
            print("GROQ API ERROR")
            print("=" * 80)
            print(type(e))
            print(e)
            print("=" * 80)
            raise


if __name__ == "__main__":
    pipeline = FinancialRAGPipeline()
    response = pipeline.query("explain 10-k summary of amazon, tesla, apple, microsoft, google")
    print("\n" + "=" * 80)
    print(response["answer"])
    print("=" * 80)