# src/rag_pipeline.py

import os
import time

os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"

import chromadb
from groq import Groq
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from prompt_templates import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

# Load .env
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
            raise ValueError("GROQ_API_KEY not found.")

        self.groq_client = Groq(api_key=api_key)

        print("RAG Pipeline Initialized Successfully.\n")

    ###############################################################

    def retrieve_context(self, query_text, top_k=4):

        print("=" * 70)
        print("STEP 1 : Retrieving Context")
        print("User Query :", query_text)

        start = time.time()

        query_vector = self.embed_model.encode([query_text]).tolist()

        results = self.collection.query(
            query_embeddings=query_vector,
            n_results=top_k
        )

        end = time.time()

        print(f"Vector Search Completed in {end-start:.2f} seconds")

        raw_documents = results["documents"][0]
        metadatas = results["metadatas"][0]

        print(f"Retrieved {len(raw_documents)} chunks.\n")

        formatted_chunks = []

        for idx in range(len(raw_documents)):

            meta = metadatas[idx]

            print(
                f"Chunk {idx+1} -> "
                f"{meta['company']} | "
                f"{meta['fiscal_year']} | "
                f"Page {meta['page_number']}"
            )

            formatted_chunks.append(
                f"--- Source Document: "
                f"{meta['company']} | "
                f"Year: {meta['fiscal_year']} | "
                f"Page: {meta['page_number']} ---\n"
                f"{raw_documents[idx]}"
            )

        print("=" * 70)

        return "\n\n".join(formatted_chunks), results

    ###############################################################

    def query(self, user_question):

        print("\n")
        print("#" * 80)
        print("NEW QUERY RECEIVED")
        print("#" * 80)

        ###########################################################

        context_str, raw_results = self.retrieve_context(user_question)

        print("\nSTEP 2 : Prompt Created")

        user_content = USER_PROMPT_TEMPLATE.format(
            context_str=context_str,
            query_str=user_question
        )

        print(f"Prompt Size : {len(user_content)} characters")

        ###########################################################

        print("\nSTEP 3 : Sending request to Groq")

        start = time.time()

        try:

            chat_completion = self.groq_client.chat.completions.create(

                model="llama-3.3-70b-versatile",

                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": user_content
                    }
                ],

                temperature=0.0
            )

            end = time.time()

            print(f"Groq Response Received in {end-start:.2f} seconds")

            answer = chat_completion.choices[0].message.content

            print("\nSTEP 4 : Answer Generated Successfully")

            print("Answer Length :", len(answer))

            print("=" * 80)

            return {
                "answer": answer,
                "raw_metadata": raw_results["metadatas"][0]
            }

        except Exception as e:

            print("\n")
            print("=" * 80)
            print("GROQ ERROR")
            print("=" * 80)
            print(type(e))
            print(e)
            print("=" * 80)

            raise


########################################################################

if __name__ == "__main__":

    pipeline = FinancialRAGPipeline()

    response = pipeline.query(
        "What risks does Apple face regarding tariffs?"
    )

    print("\n")
    print("=" * 80)
    print(response["answer"])
    print("=" * 80)