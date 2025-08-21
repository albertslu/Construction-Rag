## Construction-RAG (Backend)

RAG service (backend) for answering questions about architectural drawings using FastAPI, LangChain, Pinecone, and Supabase.

### Prerequisites
- Python 3.10+
- OpenAI API key
- Pinecone API key (serverless index)
- Optional: Supabase project (Postgres)

### Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r backend/requirements.txt
```

Create a `.env` with your keys:
```
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-large
OPENAI_EMBEDDING_DIM=3072

PINECONE_API_KEY=...
PINECONE_INDEX_NAME=construction-rag
PINECONE_CLOUD=aws
PINECONE_REGION=us-east-1
PINECONE_METRIC=cosine
PINECONE_NAMESPACE=default

SUPABASE_URL=...
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=

PORT=8000
DOCS_ENABLED=true
DATA_DIR=data/raw
```

### Initialize Pinecone Index
```bash
python -m backend.app.ingest.init_pinecone
```

### Ingest Documents
Place PDFs in `backend/data/raw/`.
```bash
python -m backend.app.ingest.ingest --data_dir backend/data/raw --namespace default
```

### Run API
```bash
uvicorn backend.app.main:app --reload --port 8000
```

- Health: GET `/healthz`
- Chat: POST `/chat` with body `{ "query": "...", "top_k": 6, "namespace": "default" }`

main