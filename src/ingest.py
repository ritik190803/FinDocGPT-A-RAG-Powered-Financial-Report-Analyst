import os
import re
import json
import pdfplumber

def extract_text_and_tables(pdf_path):
    """
    Reads a PDF file page by page, checks for tables, extracts them,
    and returns a structured list of pages containing both plain text and markdown tables.
    """
    parsed_pages = []
    
    print(f"Starting parsing for: {os.path.basename(pdf_path)}")
    
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            page_num = i + 1
            
            # 1. Try to extract structural tables from the page
            tables = page.extract_tables()
            table_markdown_strings = []
            
            if tables:
                for table in tables:
                    # Clean out None values and join rows with pipe separators for Markdown
                    cleaned_rows = []
                    for row in table:
                        cleaned_row = [str(cell).strip() if cell is not None else "" for cell in row]
                        # Only keep rows that aren't completely empty
                        if any(cleaned_row):
                            cleaned_rows.append("| " + " | ".join(cleaned_row) + " |")
                    
                    if cleaned_rows:
                        table_md = "\n".join(cleaned_rows)
                        table_markdown_strings.append(table_md)
            
            # 2. Extract plain text from the page
            raw_text = page.extract_text() or ""
            
            # 3. Clean regular text (basic regex cleanup)
            # Remove excessive consecutive whitespaces/newlines
            cleaned_text = re.sub(r'\s+', ' ', raw_text).strip()
            
            # Combine the cleaned prose text with any extracted table data
            full_page_content = cleaned_text
            if table_markdown_strings:
                full_page_content += "\n\n### Extracted Tables:\n" + "\n\n".join(table_markdown_strings)
            
            parsed_pages.append({
                "page_number": page_num,
                "content": full_page_content
            })
            
            if page_num % 50 == 0:
                print(f"  Processed {page_num}/{len(pdf.pages)} pages...")
                
    return parsed_pages

def chunk_document(pages, company, year, chunk_size=700, overlap=100):
    """
    Splits continuous text pages into overlapping chunks to ensure semantic continuity.
    Attaches critical company/year metadata to every individual chunk.
    """
    chunks = []
    
    for page in pages:
        text = page["content"]
        page_num = page["page_number"]
        
        # Simple tokenization estimation using space split
        words = text.split(" ")
        
        # Loop through words by chunk size step minus the intentional overlap
        i = 0
        while i < len(words):
            chunk_words = words[i : i + chunk_size]
            chunk_text = " ".join(chunk_words)
            
            if chunk_text.strip():
                chunks.append({
                    "chunk_text": chunk_text,
                    "metadata": {
                        "company": company,
                        "fiscal_year": year,
                        "page_number": page_num
                    }
                })
            
            # Slide index forward
            i += (chunk_size - overlap)
            
    return chunks

def run_ingestion_pipeline():
    raw_dir = "data/raw_filings"
    output_path = "data/processed_chunks.jsonl"
    all_chunks = []
    
    if not os.path.exists(raw_dir):
        print(f"Error: Directory {raw_dir} does not exist. Create it and place your PDFs inside.")
        return
        
    # Scan through all files in the folder matching our standard naming pattern
    for filename in os.listdir(raw_dir):
        if filename.endswith(".pdf"):
            pdf_path = os.path.join(raw_dir, filename)
            
            # Expecting filename format: company_year.pdf (e.g., apple_2025.pdf)
            name_without_ext = os.path.splitext(filename)[0]
            try:
                company, year = name_without_ext.split("_")
            except ValueError:
                print(f"Skipping filename '{filename}': Format must be exactly 'company_year.pdf'")
                continue
            
            # Execute step-by-step extraction and chunking
            pages = extract_text_and_tables(pdf_path)
            document_chunks = chunk_document(pages, company.capitalize(), year)
            
            all_chunks.extend(document_chunks)
            print(f"Successfully processed {filename}! Generated {len(document_chunks)} chunks.")

    # Write out the parsed dataset as a JSON Lines file
    with open(output_path, "w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk) + "\n")
            
    print(f"\nIngestion Complete! Saved total {len(all_chunks)} chunks to '{output_path}'.")

if __name__ == "__main__":
    run_ingestion_pipeline()