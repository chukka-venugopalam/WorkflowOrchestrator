# Architecture - tourism_ai

## System Architecture

Modular architecture with agent orchestration layer,
LLM integration layer, tool/plugin system, memory/persistence layer,
and monitoring/observability layer.
Vector store for semantic search and knowledge management.
Event-driven communication between components.

## Folder Structure

```
README.md
CHANGELOG.md
ARCHITECTURE.md
CONTRIBUTING.md
LICENSE
.gitignore
.env.example
requirements.txt
app/
  api/
  agents/
  tools/
  memory/
  config/
models/
  prompts/
  chains/
  embeddings/
services/
  llm/
  vector_store/
  monitoring/
data/
  knowledge/
  context/
tests/
  unit/
  integration/
scripts/
docs/
```

## Technology Stack

- **Language:** Python
- **Framework:** LangChain / LlamaIndex
- **Llm_Providers:** OpenAI / Anthropic / Open Source
- **Vector_Store:** ChromaDB / Pinecone / Qdrant
- **Database:** PostgreSQL
- **Api:** FastAPI
- **Testing:** pytest
- **Deployment:** Docker / Modal / Railway

## Services

- **Auth Service:** Authentication and authorization
- **API Gateway:** Request routing and rate limiting
- **Data Service:** Data persistence and retrieval
- **Cache Service:** In-memory caching for performance
- **LLM Service:** AI model inference and prompt management
- **Vector Store Service:** Embedding storage and semantic search
- **Agent Service:** Agent orchestration and tool management

## Database

- Primary: PostgreSQL
- Cache: Redis

## Communication Flow

Client → API Gateway → Service Layer → Data Layer
Synchronous: HTTP REST/gRPC for request-response patterns
Asynchronous: Message queue for event-driven communication
Caching: Redis cache between service and data layers
Monitoring: Centralized logging and metrics collection

## Deployment

Cloud provider (AWS/GCP/Azure) or Vercel/Railway
