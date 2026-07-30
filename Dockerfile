# Lightweight Python environment
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files including chroma_db
COPY . .

# Hugging Face Spaces defaults to port 7860
EXPOSE 7860

# Start FastAPI server
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "7860"]