# EngAgent - English Exercise Generator API

This project provides an API to generate English exercises using LangChain with or without RAG (Retrieval-Augmented Generation).

## Features

- Generate English exercises using LLM (Ollama or Google Vertex AI)
- RAG (Retrieval-Augmented Generation) support
- Grammar correction service
- Prompt template management
- Document processing (PDF, DOCX, PPTX)
- Vector database integration with ChromaDB

## Prerequisites

- Python 3.10+
- MySQL server
- [Ollama CLI](https://ollama.com) installed and configured (for local LLM)
- Google Cloud credentials (for Vertex AI)

## Quick Start with Docker

### 1. Build and Run with Docker

```bash
# Build the Docker image
docker build -t engagent-api .

# Run the container
docker run -d \
  --name engagent-api \
  -p 8000:8000 \
  --env-file .env \
  engagent-api
```

### 2. Using Docker Compose (Recommended)

Create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  engagent-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MYSQL_USER=your_mysql_user
      - MYSQL_PASSWORD=your_mysql_password
      - MYSQL_HOST=your_mysql_host
      - MYSQL_DB=your_mysql_db
      - OLLAMA_MODEL=mistral
      - HF_EMBEDDING_MODEL=sentence-transformers/all-mpnet-base-v2
    volumes:
      - ./data:/app/data
      - ./key:/app/key
    restart: unless-stopped
```

Then run:

```bash
docker-compose up -d
```

## Local Development Setup

### 1. Clone the repository
```bash
git clone <repo_url>
cd run_LLM
```

### 2. Create and activate a virtual environment
```bash
python -m venv venv
source venv/bin/activate    # on macOS/Linux
venv\Scripts\activate       # on Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
Copy `.env.example` to `.env` and update the following variables:

```env
# Database Configuration
MYSQL_USER=your_mysql_user
MYSQL_PASSWORD=your_mysql_password
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DB=your_mysql_db

# LLM Configuration
OLLAMA_MODEL=mistral
HF_EMBEDDING_MODEL=sentence-transformers/all-mpnet-base-v2

# Google Vertex AI (Optional)
USE_VERTEX=false
VERTEX_PROJECT=your_google_project
VERTEX_LOCATION=asia-southeast1
VERTEX_LLM_MODEL=gemini-pro
VERTEX_EMBEDDING_MODEL=textembedding-gecko@001
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/credentials.json
```

### 5. Run the API
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## API Endpoints

### Health Check
- `GET /health` - Check system health and component status

### Exercise Generation
- `POST /api/exercises/no-rag` - Generate exercises without RAG
- `POST /api/exercises/native-rag` - Generate exercises with RAG

### Prompt Management
- `GET /api/prompts/` - List all prompt templates
- `GET /api/prompts/{name}` - Get specific prompt template
- `POST /api/prompts/` - Create new prompt template
- `PUT /api/prompts/{name}` - Update prompt template
- `DELETE /api/prompts/{name}` - Delete prompt template
- `POST /api/prompts/{name}/generate` - Generate content using template

### Grammar Correction
- `POST /api/grammar/check` - Check and correct grammar

## Example Usage

### Generate Exercise without RAG
```bash
curl -X POST "http://localhost:8000/api/exercises/no-rag" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt_name": "english_exercise_default",
    "number": 5,
    "type": "mcq",
    "skill": "grammar",
    "level": "intermediate",
    "topic": "present perfect"
  }'
```

### Check Grammar
```bash
curl -X POST "http://localhost:8000/api/grammar/check" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "I have been to Paris last year."
  }'
```

## Project Structure

```
run_LLM/
├── app/
│   ├── api/routers/     # API endpoints
│   ├── core/           # Configuration and RAG setup
│   ├── db/             # Database session management
│   ├── models/         # SQLAlchemy models
│   ├── schemas/        # Pydantic schemas
│   ├── services/       # Business logic
│   └── main.py         # FastAPI application
├── data/               # Training data and documents
├── key/                # API keys and credentials
├── data_pipeline.py    # Document processing pipeline
├── requirements.txt    # Python dependencies
├── Dockerfile          # Docker configuration
└── README.md          # This file
```

## Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Ensure MySQL server is running
   - Check database credentials in `.env`
   - Verify database exists

2. **Ollama Connection Error**
   - Install and start Ollama: `ollama serve`
   - Pull the model: `ollama pull mistral`

3. **Google Vertex AI Error**
   - Set up Google Cloud credentials
   - Enable Vertex AI API
   - Verify project and location settings

### Health Check

Visit `http://localhost:8000/health` to check the status of all components.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.